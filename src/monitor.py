"""
ZeroFreeze - Módulo de Monitoramento
Coleta em tempo real dados de CPU, RAM (com agregação por árvore de processos e nomes amigáveis)
e Armazenamentos individuais com métricas exclusivas por partição/disco.
"""

import os
import re
import glob
import time
import subprocess
import psutil
from src.process_names import resolve_friendly_name

SESSION_MANAGERS = {
    "systemd", "gnome-shell", "cinnamon", "xfwm4", "Xorg", "gdm-wayland-session",
    "init", "lightdm", "sddm", "startxfce4", "x-session-manager"
}

from collections import deque

class SystemMonitor:
    def __init__(self, config_manager=None):
        self.config_mgr = config_manager
        self.last_disk_io = psutil.disk_io_counters(perdisk=True)
        self.last_disk_time = time.time()
        self.smart_cache = {}
        self.last_smart_check = 0
        psutil.cpu_percent(interval=None)

        # Histórico de 1 hora por sensor (1 ponto a cada 30 segundos = 120 pontos)
        self.temp_history = {}
        self.last_history_sample_time = 0

    def get_cpu_temperature(self):
        """Retorna temperatura da CPU em °C ou None."""
        try:
            # 1. Tenta via psutil sensors_temperatures
            temps = psutil.sensors_temperatures()
            if temps:
                # Prioridade: coretemp, k10temp, zenpower, cpu_thermal, acpitz
                for key in ["coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz_0", "acpitz"]:
                    if key in temps:
                        for entry in temps[key]:
                            # Prefere Package / Tctl / Tdie / composite
                            if any(w in entry.label.lower() for w in ["package", "tctl", "tdie"]) or not entry.label:
                                if entry.current and entry.current > 0:
                                    return int(round(entry.current))
                        # Se não achou com label específica, pega o primeiro válido
                        for entry in temps[key]:
                            if entry.current and entry.current > 0:
                                return int(round(entry.current))

            # 2. Fallback via /sys/class/thermal
            for zone in glob.glob("/sys/class/thermal/thermal_zone*"):
                try:
                    type_f = os.path.join(zone, "type")
                    temp_f = os.path.join(zone, "temp")
                    if os.path.exists(type_f) and os.path.exists(temp_f):
                        with open(type_f) as f:
                            z_type = f.read().strip().lower()
                        if any(k in z_type for k in ["x86_pkg_temp", "tcpu", "cpu", "acpitz"]):
                            with open(temp_f) as tf:
                                val = int(tf.read().strip())
                                if val > 1000:
                                    val = val / 1000.0
                                if 15 <= val <= 115:
                                    return int(round(val))
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def get_ram_temperature(self):
        """
        Retorna dicionário {'is_digital': bool, 'temp': int or None} para a memória RAM.
        No Linux, sensores DIMM físicos usam jc42 ou i2c-eeprom (raro em desktops comuns).
        Se não houver sensor físico em hardware suportado, retorna temp: None.
        """
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for key, entries in temps.items():
                    if "jc42" in key.lower() or "dimm" in key.lower() or "dram" in key.lower() or "ram" in key.lower():
                        for entry in entries:
                            if entry.current and entry.current > 0:
                                return {"is_digital": False, "temp": int(round(entry.current))}
        except Exception:
            pass
        return {"is_digital": False, "temp": None}

    def get_ram_metrics(self):
        """Retorna estatísticas globais de memória RAM incluindo telemetria térmica."""
        v = psutil.virtual_memory()
        temp_data = self.get_ram_temperature()
        return {
            "percent": round(v.percent, 1),
            "total_gb": round(v.total / (1024 ** 3), 2),
            "used_gb": round(v.used / (1024 ** 3), 2),
            "available_gb": round(v.available / (1024 ** 3), 2),
            "temp": temp_data.get("temp"),
            "is_digital": temp_data.get("is_digital", False)
        }

    def get_cpu_metrics(self):
        """Retorna uso de CPU global e temperatura atual."""
        cpu_p = psutil.cpu_percent(interval=None)
        cpu_temp = self.get_cpu_temperature()
        return {
            "percent": round(cpu_p, 1),
            "count": psutil.cpu_count(logical=True),
            "temp": cpu_temp
        }

    def get_all_hardware_temperatures(self):
        """
        Coleta e categoriza todos os sensores de temperatura de hardware disponíveis:
        - CPU (Package e Cores)
        - Placa-Mãe / Gabinete (acpitz, thermal_zones)
        - Drives NVMe / SSDs
        - Placa de Rede / Wi-Fi
        Mantém o histórico de 1 hora (amostras a cada ~30s ou a cada chamada)
        e calcula a máxima temperatura global para a dock.
        """
        sensors_list = []
        now = time.time()
        should_record = (now - self.last_history_sample_time >= 25.0)

        # 1. CPU (Package id 0 e núcleos)
        temps = {}
        try:
            temps = psutil.sensors_temperatures() or {}
        except Exception:
            pass

        # CPU Package
        cpu_package_temp = self.get_cpu_temperature()
        if cpu_package_temp is not None:
            sensors_list.append({
                "id": "cpu_package",
                "name": "Processador (CPU)",
                "category": "cpu",
                "current": cpu_package_temp
            })

        # Placa-mãe / Gabinete (acpitz_0 ou thermal_zone0)
        mb_temp = None
        if "acpitz_0" in temps and temps["acpitz_0"]:
            entry = temps["acpitz_0"][0]
            if entry.current and entry.current > 0:
                mb_temp = int(round(entry.current))
        elif "acpitz" in temps and temps["acpitz"]:
            entry = temps["acpitz"][0]
            if entry.current and entry.current > 0:
                mb_temp = int(round(entry.current))

        if mb_temp is not None:
            sensors_list.append({
                "id": "motherboard",
                "name": "Placa-mãe / Gabinete",
                "category": "motherboard",
                "current": mb_temp
            })

        # Drives NVMe / Armazenamento
        nvme_idx = 1
        for h in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
            try:
                name_f = os.path.join(h, "name")
                if os.path.exists(name_f):
                    with open(name_f) as f:
                        h_name = f.read().strip()
                    if h_name == "nvme":
                        temp_f = os.path.join(h, "temp1_input")
                        if os.path.exists(temp_f):
                            with open(temp_f) as tf:
                                val = int(round(int(tf.read().strip()) / 1000.0))
                            dev_name = os.path.basename(os.path.realpath(os.path.join(h, "device")))
                            sensors_list.append({
                                "id": f"nvme_{dev_name}",
                                "name": f"SSD NVMe ({dev_name.upper()})",
                                "category": "disk",
                                "current": val
                            })
                            nvme_idx += 1
            except Exception:
                pass

        # Sensores de Circuito / Alimentação (SEN2, SEN3)
        for zone in sorted(glob.glob("/sys/class/thermal/thermal_zone*")):
            try:
                type_f = os.path.join(zone, "type")
                temp_f = os.path.join(zone, "temp")
                if os.path.exists(type_f) and os.path.exists(temp_f):
                    with open(type_f) as f:
                        z_type = f.read().strip()
                    if z_type in ["SEN2", "SEN3", "TCPU_PCI"]:
                        with open(temp_f) as tf:
                            val = int(round(int(tf.read().strip()) / 1000.0))
                        name_display = "Circuito de Alimentação (VRM)" if z_type == "SEN2" else f"Sensor Interno ({z_type})"
                        sensors_list.append({
                            "id": f"thermal_{z_type}",
                            "name": name_display,
                            "category": "chipset",
                            "current": val
                        })
            except Exception:
                pass

        # Placa de Rede / Wi-Fi (mt7921_phy0)
        if "mt7921_phy0" in temps and temps["mt7921_phy0"]:
            entry = temps["mt7921_phy0"][0]
            if entry.current and entry.current > 0:
                sensors_list.append({
                    "id": "wifi_chip",
                    "name": "Placa Wi-Fi / Bluetooth",
                    "category": "network",
                    "current": int(round(entry.current))
                })

        # Atualiza histórico de 1 hora (120 amostras)
        if should_record or not self.temp_history:
            self.last_history_sample_time = now
            for s in sensors_list:
                sid = s["id"]
                if sid not in self.temp_history:
                    # Inicializa com 10 pontos repetidos do valor inicial para desenhar a sparkline de imediato
                    self.temp_history[sid] = deque([s["current"]] * 10, maxlen=120)
                else:
                    self.temp_history[sid].append(s["current"])

        # Enriquecer cada sensor com Mínima, Máxima e Lista de Pontos
        max_overall_temp = 0
        for s in sensors_list:
            sid = s["id"]
            pts = list(self.temp_history.get(sid, [s["current"]]))
            s["min"] = min(pts) if pts else s["current"]
            s["max"] = max(pts) if pts else s["current"]
            s["points"] = pts
            if s["current"] > max_overall_temp:
                max_overall_temp = s["current"]

        return {
            "max_overall_temp": max_overall_temp,
            "sensors": sensors_list
        }


    def get_top_memory_apps(self, limit=5):
        """
        Retorna as aplicações que mais consomem memória RAM,
        agrupando todos os subprocessos sob a aplicação raiz e traduzindo para nomes amigáveis.
        """
        use_friendly = True
        if self.config_mgr:
            use_friendly = self.config_mgr.get("ui", "use_friendly_names", True)

        processes = {}
        for p in psutil.process_iter(["pid", "ppid", "name", "memory_info", "cmdline"]):
            try:
                processes[p.info["pid"]] = p.info
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        total_sys_ram = psutil.virtual_memory().total
        app_groups = {}

        for pid, info in processes.items():
            name = info.get("name") or "desconhecido"
            mem_info = info.get("memory_info")
            rss = mem_info.rss if mem_info else 0

            # Navega na árvore até a raiz da aplicação
            curr = pid
            root_pid = pid
            root_name = name

            while curr in processes:
                ppid = processes[curr].get("ppid", 0)
                if ppid <= 1 or ppid not in processes:
                    break
                p_parent = processes[ppid]
                p_name = p_parent.get("name", "")
                if p_name in SESSION_MANAGERS:
                    break
                curr = ppid
                root_pid = curr
                root_name = p_name

            if root_pid not in app_groups:
                app_groups[root_pid] = {
                    "root_pid": root_pid,
                    "raw_name": root_name,
                    "cmdline": processes.get(root_pid, {}).get("cmdline", []),
                    "total_rss": 0,
                    "pids": []
                }
            app_groups[root_pid]["total_rss"] += rss
            app_groups[root_pid]["pids"].append(pid)

        # Ordena pelo consumo consolidado
        sorted_apps = sorted(app_groups.values(), key=lambda x: x["total_rss"], reverse=True)

        result = []
        for app in sorted_apps[:limit]:
            mb = app["total_rss"] / (1024 * 1024)
            gb = mb / 1024
            pct = (app["total_rss"] / total_sys_ram) * 100 if total_sys_ram > 0 else 0
            size_str = f"{gb:.2f} GB" if gb >= 1.0 else f"{mb:.0f} MB"

            # Resolve filhos para identificar apps dentro de sandbox Flatpak (bwrap)
            children_info = [processes.get(p, {}) for p in app["pids"]]
            
            if use_friendly:
                display_name = resolve_friendly_name(app["raw_name"], app["cmdline"], children_info)
            else:
                display_name = app["raw_name"]

            cmd_str = " ".join(app["cmdline"]) if app["cmdline"] else app["raw_name"]

            # Identifica se a aplicação está protegida pela Whitelist
            is_whitelisted = False
            if self.config_mgr:
                wl = set(w.lower() for w in self.config_mgr.get("safety", "whitelist", []))
                raw_lower = app["raw_name"].lower()
                name_lower = display_name.lower()
                cmd_lower = cmd_str.lower()
                is_whitelisted = (
                    raw_lower in wl or
                    name_lower in wl or
                    any(w in raw_lower or w in name_lower or (len(w) > 3 and w in cmd_lower) for w in wl)
                )

            result.append({
                "root_pid": app["root_pid"],
                "name": display_name,
                "raw_name": app["raw_name"],
                "cmdline_str": cmd_str,
                "process_count": len(app["pids"]),
                "size_str": size_str,
                "percent": round(pct, 1),
                "total_bytes": app["total_rss"],
                "is_whitelisted": is_whitelisted
            })
        return result

    def get_top_cpu_apps(self, limit=5):
        """
        Retorna as 5 aplicações que mais consomem CPU com nomes amigáveis.
        """
        use_friendly = True
        if self.config_mgr:
            use_friendly = self.config_mgr.get("ui", "use_friendly_names", True)

        processes = {}
        for p in psutil.process_iter(["pid", "ppid", "name", "cpu_percent", "cmdline"]):
            try:
                processes[p.info["pid"]] = p.info
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        app_groups = {}
        for pid, info in processes.items():
            name = info.get("name") or "desconhecido"
            cpu_p = info.get("cpu_percent") or 0.0

            curr = pid
            root_pid = pid
            root_name = name

            while curr in processes:
                ppid = processes[curr].get("ppid", 0)
                if ppid <= 1 or ppid not in processes:
                    break
                p_parent = processes[ppid]
                p_name = p_parent.get("name", "")
                if p_name in SESSION_MANAGERS:
                    break
                curr = ppid
                root_pid = curr
                root_name = p_name

            if root_pid not in app_groups:
                app_groups[root_pid] = {
                    "root_pid": root_pid,
                    "raw_name": root_name,
                    "cmdline": processes.get(root_pid, {}).get("cmdline", []),
                    "total_cpu": 0.0,
                    "pids": []
                }
            app_groups[root_pid]["total_cpu"] += cpu_p
            app_groups[root_pid]["pids"].append(pid)

        sorted_apps = sorted(app_groups.values(), key=lambda x: x["total_cpu"], reverse=True)
        result = []
        for app in sorted_apps[:limit]:
            children_info = [processes.get(p, {}) for p in app["pids"]]
            if use_friendly:
                display_name = resolve_friendly_name(app["raw_name"], app["cmdline"], children_info)
            else:
                display_name = app["raw_name"]

            cmd_str = " ".join(app["cmdline"]) if app["cmdline"] else app["raw_name"]

            # Identifica se a aplicação está protegida pela Whitelist
            is_whitelisted = False
            if self.config_mgr:
                wl = set(w.lower() for w in self.config_mgr.get("safety", "whitelist", []))
                raw_lower = app["raw_name"].lower()
                name_lower = display_name.lower()
                cmd_lower = cmd_str.lower()
                is_whitelisted = (
                    raw_lower in wl or
                    name_lower in wl or
                    any(w in raw_lower or w in name_lower or (len(w) > 3 and w in cmd_lower) for w in wl)
                )

            result.append({
                "root_pid": app["root_pid"],
                "name": display_name,
                "raw_name": app["raw_name"],
                "cmdline_str": cmd_str,
                "process_count": len(app["pids"]),
                "percent": round(app["total_cpu"], 1),
                "is_whitelisted": is_whitelisted
            })
        return result

    def get_storage_metrics(self):
        """
        Detecta e isola cada partição/disco físico real do usuário.
        Deduplica sistemas compartilhados e calcula estatísticas exclusivas.
        """
        partitions = psutil.disk_partitions(all=False)
        disks_data = []
        seen_devices = set()

        now = time.time()
        elapsed = max(0.1, now - self.last_disk_time)
        curr_perdisk_io = psutil.disk_io_counters(perdisk=True)

        for p in partitions:
            # Ignora partições virtuais, snap, boot e partições de loop
            if (p.device.startswith("/dev/loop") or 
                "squashfs" in p.fstype or 
                p.mountpoint.startswith("/var/snap") or
                p.mountpoint in ["/boot", "/boot/efi"]):
                continue

            # Evita duplicar o mesmo filesystem se montado em / e /home
            if p.device in seen_devices:
                continue
            seen_devices.add(p.device)

            try:
                usage = psutil.disk_usage(p.mountpoint)
                name = self._format_disk_name(p.mountpoint, p.device)
                disk_id = os.path.basename(p.device)

                # Calcula velocidades exclusivas desta partição/disco
                disk_base = disk_id.rstrip("0123456789p")
                read_mb_s = 0.0
                write_mb_s = 0.0

                if self.last_disk_io and curr_perdisk_io:
                    # Tenta ler io pelo nome base (ex: nvme0n1) ou da partição
                    io_curr = curr_perdisk_io.get(disk_id) or curr_perdisk_io.get(disk_base)
                    io_last = self.last_disk_io.get(disk_id) or self.last_disk_io.get(disk_base)
                    if io_curr and io_last:
                        r_delta = io_curr.read_bytes - io_last.read_bytes
                        w_delta = io_curr.write_bytes - io_last.write_bytes
                        read_mb_s = max(0.0, (r_delta / (1024 * 1024)) / elapsed)
                        write_mb_s = max(0.0, (w_delta / (1024 * 1024)) / elapsed)

                # Informações de integridade e SMART
                smart_info = self._get_smart_info(disk_base)
                temp_info = self._get_disk_temperature(p.device, p.fstype, smart_info)

                disks_data.append({
                    "mountpoint": p.mountpoint,
                    "device": p.device,
                    "disk_base": disk_base,
                    "label": name,
                    "fstype": p.fstype,
                    "percent": round(usage.percent, 1),
                    "total_gb": round(usage.total / (1024 ** 3), 1),
                    "used_gb": round(usage.used / (1024 ** 3), 1),
                    "free_gb": round(usage.free / (1024 ** 3), 1),
                    "read_mb_s": round(read_mb_s, 1),
                    "write_mb_s": round(write_mb_s, 1),
                    "smart": smart_info,
                    "temp": temp_info.get("temp"),
                    "is_digital": temp_info.get("is_digital", False)
                })
            except (PermissionError, FileNotFoundError):
                continue

        self.last_disk_io = curr_perdisk_io
        self.last_disk_time = now

        return {"disks": disks_data}

    def _get_smart_info(self, disk_base):
        """Consulta saúde SMART via UDisks2."""
        now = time.time()
        if disk_base in self.smart_cache and (now - self.last_smart_check < 60):
            return self.smart_cache[disk_base]

        info = {
            "health": "Saudável",
            "temp_c": None,
            "status": "Normal"
        }

        try:
            # Consulta via udisksctl
            dev_path = f"/dev/{disk_base}"
            cmd = ["udisksctl", "info", "-b", dev_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1.5)
            if res.returncode == 0:
                out = res.stdout
                if "SmartSelftestStatus:                success" in out or "SmartFailing:               false" in out:
                    info["health"] = "Saudável"
                # Extrai temperatura se disponível (em Kelvin)
                for line in out.splitlines():
                    if "SmartTemperature:" in line:
                        parts = line.split(":")
                        if len(parts) > 1:
                            try:
                                k = float(parts[1].strip())
                                if k > 200:  # Kelvin
                                    info["temp_c"] = int(round(k - 273.15))
                            except ValueError:
                                pass
        except Exception:
            pass

        self.smart_cache[disk_base] = info
        self.last_smart_check = now
        return info

    def _format_disk_name(self, mountpoint, device):
        """Retorna um nome limpo e compreensível para cada partição/disco."""
        if mountpoint == "/":
            return "Sistema (/)"
        elif mountpoint == "/home":
            return "Pasta Home"
        elif "6f19abb3" in mountpoint:
            return "SSD Secundário"
        base = os.path.basename(mountpoint)
        return f"Disco ({base})" if base else f"Disco ({os.path.basename(device)})"

    def _get_disk_temperature(self, device_path, fstype, smart_info=None):
        """
        Retorna {'is_digital': bool, 'temp': int or None}
        - Dispositivos digitais/virtuais/rede: is_digital = True, temp = None
        - Dispositivos físicos sem leitura: is_digital = False, temp = None
        - Dispositivos físicos com leitura: is_digital = False, temp = graus °C
        """
        # Se não for caminho de bloco físico em /dev/
        if not device_path or not device_path.startswith("/dev/"):
            return {"is_digital": True, "temp": None}

        # Sistemas virtuais, loop, squashfs, montagens de rede/fuse
        virtual_fs = {
            "nfs", "cifs", "smbfs", "fuse", "fuse.google-drive-ocamlfuse",
            "tmpfs", "ramfs", "squashfs", "overlay", "iso9660", "vboxsf"
        }
        if fstype and fstype.lower() in virtual_fs:
            return {"is_digital": True, "temp": None}

        base_dev = os.path.basename(device_path)
        if base_dev.startswith("loop") or base_dev.startswith("zram") or base_dev.startswith("ram"):
            return {"is_digital": True, "temp": None}

        # 1. Se smart_info já encontrou temperatura
        if smart_info and smart_info.get("temp_c") is not None:
            return {"is_digital": False, "temp": smart_info["temp_c"]}

        # 2. Tenta leitura via hwmon para controladoras NVMe
        m_nvme = re.match(r"^(nvme\d+)n\d+", base_dev)
        if m_nvme:
            ctrl_name = m_nvme.group(1)
            for h in glob.glob("/sys/class/hwmon/hwmon*"):
                try:
                    name_f = os.path.join(h, "name")
                    dev_f = os.path.join(h, "device")
                    if os.path.exists(name_f):
                        with open(name_f) as f:
                            if f.read().strip() == "nvme":
                                target = os.path.realpath(dev_f)
                                if os.path.basename(target) == ctrl_name:
                                    temp_input = os.path.join(h, "temp1_input")
                                    if os.path.exists(temp_input):
                                        with open(temp_input) as tf:
                                            return {"is_digital": False, "temp": int(round(int(tf.read().strip()) / 1000.0))}
                except Exception:
                    pass

        # 3. Tenta hwmon de bloco para SATA/SCSI (sdX)
        m_sd = re.match(r"^(sd[a-z]|hd[a-z])", base_dev)
        if m_sd:
            disk_base = m_sd.group(1)
            for temp_f in glob.glob(f"/sys/block/{disk_base}/device/hwmon/hwmon*/temp1_input"):
                try:
                    with open(temp_f) as tf:
                        return {"is_digital": False, "temp": int(round(int(tf.read().strip()) / 1000.0))}
                except Exception:
                    pass

        # Dispositivo físico sem leitura térmica disponível
        return {"is_digital": False, "temp": None}

