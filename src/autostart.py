"""
ZeroFreeze - Módulo de Inicialização Automática (Autostart)
Permite ativar/desativar a inicialização automática do ZeroFreeze no login do usuário.
"""

import os

AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
DESKTOP_FILE = os.path.join(AUTOSTART_DIR, "zerofreeze.desktop")

def is_autostart_enabled() -> bool:
    """Verifica se o ZeroFreeze está configurado para iniciar automaticamente."""
    if not os.path.exists(DESKTOP_FILE):
        return False
    try:
        with open(DESKTOP_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            if "X-GNOME-Autostart-enabled=false" in content:
                return False
        return True
    except Exception:
        return False

def set_autostart(enabled: bool) -> bool:
    """Ativa ou desativa a inicialização automática do ZeroFreeze."""
    try:
        if not os.path.exists(AUTOSTART_DIR):
            os.makedirs(AUTOSTART_DIR, exist_ok=True)

        if enabled:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            run_script = os.path.join(base_dir, "run.sh")
            if os.path.exists("/usr/bin/zerofreeze"):
                exec_cmd = "/usr/bin/zerofreeze"
                icon_val = "zerofreeze"
            else:
                exec_cmd = run_script
                icon_val = os.path.join(base_dir, "assets", "icons", "zerofreeze.png")

            desktop_content = f"""[Desktop Entry]
Type=Application
Name=ZeroFreeze
Comment=Monitor & Salvaguarda Anti-Freeze
Exec={exec_cmd}
Icon={icon_val}
Terminal=false
Categories=Utility;System;
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""
            with open(DESKTOP_FILE, "w", encoding="utf-8") as f:
                f.write(desktop_content)
            return True
        else:
            if os.path.exists(DESKTOP_FILE):
                os.remove(DESKTOP_FILE)
            return True
    except Exception as e:
        print(f"[ZeroFreeze] Erro ao configurar autostart: {e}")
        return False
