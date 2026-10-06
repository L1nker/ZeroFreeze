"""
ZeroFreeze - Módulo de Salvaguarda Anti-Freeze
Gerencia a regra de alerta (padrão 90%), corte cirúrgico (padrão 93%),
lista de proteção (whitelist), autopreservação e Sentinela em Thread Independente.
"""

import os
import signal
import subprocess
import threading
import time
import psutil
from src.history import add_history_event

class AntiFreezeGuard:
    def __init__(self, config_manager, monitor):
        self.config_mgr = config_manager
        self.monitor = monitor
        self.my_pid = os.getpid()

        self.last_sound_alert_time = 0
        self.sound_alert_cooldown = 40  # segundos entre bipes para não incomodar
        self.alert_armed = True

        self._running = False
        self._worker_thread = None
        self._prev_app_memory = {}  # {app_name: (mb, timestamp)}
        self._last_spike_check = 0

    def start_sentinel(self):
        """Inicia a thread sentinela independente em segundo plano."""
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._sentinel_loop, name="ZeroFreeze-Sentinel", daemon=True)
        self._worker_thread.start()
        print("[ZeroFreeze] Sentinela Anti-Freeze em thread independente iniciada com sucesso.")

    def stop_sentinel(self):
        """Para a thread sentinela."""
        self._running = False

    def _sentinel_loop(self):
        """
        Loop em thread dedicada de alta frequência.
        Não depende da fila de eventos da interface gráfica (GTK),
        garantindo resposta em milissegundos mesmo sob estresse severo de memória.
        """
        while self._running:
            try:
                # Leitura instantânea da memória virtual do Linux
                v = psutil.virtual_memory()
                current_ram_pct = v.percent

                cfg_sound = float(self.config_mgr.get("safety", "sound_threshold_percent", 90.0))
                kill_threshold = float(self.config_mgr.get("safety", "kill_threshold_percent", 93.0))

                now = time.time()

                # Re-armar alerta se a memória caiu para zona segura
                if current_ram_pct < (cfg_sound - 4.0):
                    self.alert_armed = True

                # 1. Alerta Sonoro aos 90% (ou configurado)
                if current_ram_pct >= cfg_sound:
                    sound_enabled = self.config_mgr.get("safety", "sound_alert_enabled", True)
                    if sound_enabled and self.alert_armed and (now - self.last_sound_alert_time > self.sound_alert_cooldown):
                        self._trigger_warning_alert(round(current_ram_pct, 1))
                        self.last_sound_alert_time = now
                        self.alert_armed = False

                # 2. Salvaguarda Anti-Travamento aos 93% (ou configurado)
                if current_ram_pct >= kill_threshold:
                    print(f"[ZeroFreeze] [SENTINELA] RAM CRÍTICA: {current_ram_pct:.1f}% >= {kill_threshold:.1f}%! Intervenção emergencial!")
                    whitelist = set(w.lower() for w in self.config_mgr.get("safety", "whitelist", []))
                    self._execute_kill_safeguard(whitelist, round(current_ram_pct, 1))
                    # Breve pausa após o abate para permitir liberação das páginas pelo kernel
                    time.sleep(0.5)

                # 3. Detecção de picos anormais de consumo (se RAM >= 70%)
                if current_ram_pct >= 70.0 and (now - self._last_spike_check > 4.0):
                    self._check_memory_spikes(current_ram_pct)
                    self._last_spike_check = now

                # Cadência de verificação dinâmica (sentinela rápida):
                # Se estiver acima de 85%, verifica a cada 120ms para impedir o Swap Thrashing.
                # Em uso normal (<85%), verifica a cada 0.8s para poupar CPU.
                if current_ram_pct >= 85.0:
                    time.sleep(0.12)
                else:
                    time.sleep(0.8)

            except Exception as e:
                time.sleep(1.0)

    def check_and_safeguard(self, ram_metrics=None):
        """
        Método de checagem direta (compatibilidade com chamadas da UI).
        """
        if not ram_metrics:
            ram_metrics = self.monitor.get_ram_metrics()

        current_ram_pct = ram_metrics["percent"]
        cfg_sound = float(self.config_mgr.get("safety", "sound_threshold_percent", 90.0))
        kill_threshold = float(self.config_mgr.get("safety", "kill_threshold_percent", 93.0))
        sound_enabled = self.config_mgr.get("safety", "sound_alert_enabled", True)
        whitelist = set(w.lower() for w in self.config_mgr.get("safety", "whitelist", []))

        now = time.time()

        if current_ram_pct < (cfg_sound - 4.0):
            self.alert_armed = True

        if current_ram_pct >= cfg_sound:
            if sound_enabled and self.alert_armed and (now - self.last_sound_alert_time > self.sound_alert_cooldown):
                self._trigger_warning_alert(current_ram_pct)
                self.last_sound_alert_time = now
                self.alert_armed = False

        if current_ram_pct >= kill_threshold:
            print(f"[ZeroFreeze] ALERTA CRÍTICO: RAM atingiu {current_ram_pct}%! Acionando salvaguarda...")
            return self._execute_kill_safeguard(whitelist, current_ram_pct)

        return None

    def _trigger_warning_alert(self, percent):
        """Dispara aviso sonoro, notificação sutil e registra no histórico."""
        print(f"[ZeroFreeze] Aviso: RAM atingiu {percent}%. Emitindo alerta sonoro.")

        # Identifica aplicação líder de consumo para o histórico
        top_name = "Sistema"
        top_mb = 0.0
        try:
            top_apps = self.monitor.get_top_memory_apps(limit=1)
            if top_apps:
                top_name = top_apps[0]["name"]
                top_mb = top_apps[0].get("memory_mb", 0.0)
        except Exception:
            pass

        add_history_event("ALERT", top_name, top_mb, percent, "Alerta preventivo de RAM acionado")

        try:
            subprocess.Popen(
                ["canberra-gtk-play", "-i", "dialog-warning"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

        try:
            subprocess.Popen(
                ["notify-send", "-u", "normal", "-i", "dialog-warning",
                 "ZeroFreeze: Memória em Alerta",
                 f"O consumo de RAM atingiu {percent}%. Limite preventivo acionado."],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    def _check_memory_spikes(self, current_ram_pct):
        """
        Rastreia processos que apresentaram aumento repentino e anormal de consumo
        (ex: saltos bruscos acima de 750 MB em poucos segundos) e registra no histórico.
        """
        try:
            now = time.time()
            top_apps = self.monitor.get_top_memory_apps(limit=8)
            for app in top_apps:
                name = app["name"]
                mem_mb = app.get("memory_mb", 0.0)

                if name in self._prev_app_memory:
                    prev_mb, prev_time = self._prev_app_memory[name]
                    dt = max(1.0, now - prev_time)
                    diff_mb = mem_mb - prev_mb

                    if diff_mb > 750.0 and dt <= 15.0:
                        add_history_event(
                            "SPIKE",
                            name,
                            mem_mb,
                            current_ram_pct,
                            f"Crescimento súbito de +{diff_mb:.0f} MB em {dt:.0f}s"
                        )
                self._prev_app_memory[name] = (mem_mb, now)
        except Exception:
            pass

    def _execute_kill_safeguard(self, whitelist, percent):
        """Localiza a aplicação mais pesada e encerra com segurança para salvar o sistema."""
        top_apps = self.monitor.get_top_memory_apps(limit=15)
        my_tree_pids = self._get_my_process_tree()

        target_app = None
        for app in top_apps:
            raw_name = app["raw_name"].lower()
            name = app["name"].lower()
            root_pid = app["root_pid"]

            # Autopreservação: nunca matar o ZeroFreeze
            if root_pid == self.my_pid or root_pid in my_tree_pids:
                continue

            # Whitelist: ignorar se estiver protegido
            if raw_name in whitelist or name in whitelist:
                print(f"[ZeroFreeze] Ignorando '{app['name']}' (está na whitelist).")
                continue

            # Processos raiz do sistema essenciais
            if root_pid <= 100 or raw_name in ["systemd", "gnome-shell", "cinnamon", "xorg", "wayland", "mutter"]:
                continue

            target_app = app
            break

        if not target_app:
            print("[ZeroFreeze] Nenhum aplicativo elegível para finalização fora da whitelist!")
            return None

        # Finalização da aplicação
        root_pid = target_app["root_pid"]
        app_name = target_app["name"]
        print(f"[ZeroFreeze] SALVAGUARDA DE EMERGÊNCIA: Abatendo '{app_name}' (PID {root_pid}) para salvar o sistema...")

        killed_success = self.kill_application_tree(root_pid)

        if killed_success:
            # Registra no histórico oficial de salvamentos
            add_history_event(
                "KILL",
                app_name,
                target_app.get("memory_mb", 0.0),
                percent,
                f"Encerramento de emergência (PID {root_pid}) para impedir travamento do Linux"
            )

            # Notifica o usuário do salvamento
            try:
                subprocess.Popen(
                    ["canberra-gtk-play", "-i", "dialog-error"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                subprocess.Popen(
                    ["notify-send", "-u", "critical", "-i", "dialog-error",
                     "❄️ ZeroFreeze: Sistema Salvo de Congelamento!",
                     f"A memória chegou a {percent}%. '{app_name}' foi encerrado com sucesso para evitar o travamento."],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass
            return {"killed": True, "app": target_app}

        return {"killed": False, "app": target_app}

    def kill_application_tree(self, root_pid):
        """
        Encerra cirurgicamente o processo-pai e todos os seus filhos.
        Tenta SIGTERM de forma rápida (300ms); caso ainda resista, força SIGKILL imediatamente.
        """
        try:
            parent = psutil.Process(root_pid)
            children = parent.children(recursive=True)

            # Envia SIGTERM para todos
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            parent.terminate()

            # Aguarda até 300ms de forma ágil para não travar
            _, alive = psutil.wait_procs(children + [parent], timeout=0.35)

            # Força SIGKILL imediato nos sobreviventes
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass

            return True
        except psutil.NoSuchProcess:
            return True
        except Exception as e:
            print(f"[ZeroFreeze] Erro ao encerrar processo {root_pid}: {e}")
            return False

    def _get_my_process_tree(self):
        """Retorna todos os PIDs pertencentes à árvore do próprio ZeroFreeze."""
        pids = {self.my_pid}
        try:
            me = psutil.Process(self.my_pid)
            for c in me.children(recursive=True):
                pids.add(c.pid)
        except Exception:
            pass
        return pids
