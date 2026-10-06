"""
ZeroFreeze - Ponto de Entrada Principal
Inicializa o monitor de sistema, o motor de salvaguarda anti-freeze e a interface do widget.
"""

import sys
import os
import signal
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

# Adiciona o diretório raiz ao path de importação
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.config import ConfigManager
from src.monitor import SystemMonitor
from src.anti_freeze import AntiFreezeGuard
from src.ui.widget_window import WidgetWindow

def main():
    print("==================================================")
    print("❄️  ZeroFreeze - Monitor & Salvaguarda Anti-Freeze")
    print("==================================================")

    # 1. Carrega configurações
    cfg_mgr = ConfigManager()

    # 2. Inicializa o monitor de hardware e processos
    monitor = SystemMonitor()

    # 3. Inicializa o motor de salvaguarda anti-freeze
    guard = AntiFreezeGuard(cfg_mgr, monitor)
    guard.start_sentinel()

    # 4. Inicializa a janela do Widget
    window = WidgetWindow(cfg_mgr, monitor, guard)

    # Captura Ctrl+C no terminal
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, Gtk.main_quit)

    window.show_all()
    print("[ZeroFreeze] Widget inicializado com sucesso!")
    print("[ZeroFreeze] Monitoramento de CPU, RAM e Armazenamento ativo.")
    print(f"[ZeroFreeze] Salvaguarda anti-travamento armada: Alerta a {cfg_mgr.get('safety', 'sound_threshold_percent')}% | Finalização preventiva a {cfg_mgr.get('safety', 'kill_threshold_percent')}%.")

    Gtk.main()

if __name__ == "__main__":
    main()
