"""
ZeroFreeze - Módulo de Monitoramento
Coleta em tempo real dados de CPU, RAM (com agregação por árvore de processos e nomes amigáveis)
e Armazenamentos individuais com métricas exclusivas por partição/disco.
"""

import os
import time
import subprocess
import psutil
from src.process_names import resolve_friendly_name

SESSION_MANAGERS = {
    "systemd", "gnome-shell", "cinnamon", "xfwm4", "Xorg", "gdm-wayland-session",
    "init", "lightdm", "sddm", "startxfce4", "x-session-manager"
}

class SystemMonitor:
    def __init__(self, config_manager=None):
        self.config_mgr = config_manager
        self.last_disk_io = psutil.disk_io_counters(perdisk=True)
        self.last_disk_time = time.time()
        self.smart_cache = {}
        self.last_smart_check = 0
        psutil.cpu_percent(interval=None)

    def get_ram_metrics(self):
        """Retorna estatísticas globais de memória RAM."""
        v = psutil.virtual_memory()
        return {
            "percent": round(v.percent, 1),
            "total_gb": round(v.total / (1024 ** 3), 2),
            "used_gb": round(v.used / (1024 ** 3), 2),
            "available_gb": round(v.available / (1024 ** 3), 2)
        }

    def get_cpu_metrics(self):
        """Retorna uso de CPU global."""
        cpu_p = psutil.cpu_percent(interval=None)
        return {
            "percent": round(cpu_p, 1),
            "count": psutil.cpu_count(logical=True)
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

            result.append({
                "root_pid": app["root_pid"],
                "name": display_name,
                "raw_name": app["raw_name"],
                "cmdline_str": cmd_str,
                "process_count": len(app["pids"]),
                "size_str": size_str,
                "percent": round(pct, 1),
                "total_bytes": app["total_rss"]
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

            result.append({
                "root_pid": app["root_pid"],
                "name": display_name,
                "raw_name": app["raw_name"],
                "cmdline_str": cmd_str,
                "process_count": len(app["pids"]),
                "percent": round(app["total_cpu"], 1)
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
                    "smart": smart_info
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
