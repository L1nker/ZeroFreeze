"""
ZeroFreeze - Módulo de Configuração
Gerencia o carregamento, validação e persistência das configurações do usuário.
"""

import json
import os

DEFAULT_CONFIG = {
    "dock": {
        "edge": "right",              # "right", "left", "top", "bottom"
        "offset_percent": 69,         # 0 a 100 (posição calibrada pelo Linker)
        "auto_hide": False,
        "trigger_mode": "hover",      # "hover" ou "click"
        "peek_size_px": 8,            # Tamanho da bordinha sutil visível
        "dock_width": 72,
        "dock_height": 260,
        "target_monitor": "primary",   # "primary" ou índice "0", "1"...
        "scale_percent": 69,          # Tamanho Geral calibrado pelo Linker (69%)
        "circle_blue_diam": 87,       # Silhueta analítica consolidada
        "circle_red_diam": 109,
        "pos_blue_circle": 18,
        "pos_red_circle": 111,
        "tail_size_px": 53,
        "element_spacing": 8,         # Distância entre elementos calibrada pelo Linker
        "base_middle_height": 243,    # Altura da base (Fatia 2) calibrada pelo Linker
        "element_order": ["ram", "cpu", "storage"],  # Ordem padrão dos elementos na dock
        "notch_enabled": True         # Barrinha luminosa (entalhe) quando recolhido
    },
    "colors": {
        "background_r": 0.06,
        "background_g": 0.07,
        "background_b": 0.09,
        "background_a": 0.94,
        "ram_ring": [1.0, 0.45, 0.0],
        "cpu_ring": [0.15, 0.85, 0.55],
        "disk_ring": [0.95, 0.80, 0.15],
        "notch_color": [0.0, 0.28, 1.0]  # Cor do entalhe luminoso (azul elétrico padrão)
    },
    "safety": {
        "sound_alert_enabled": True,
        "sound_threshold_percent": 90.0,
        "kill_threshold_percent": 93.0,
        "whitelist": [
            "ZeroFreeze",
            "python3",
            "gnome-shell",
            "cinnamon",
            "xfwm4",
            "Xorg",
            "systemd",
            "systemd-udevd",
            "pulseaudio",
            "pipewire",
            "gdm",
            "lightdm",
            "dbus-daemon",
            "mutter"
        ]
    },
    "ui": {
        "show_manual_kill_buttons": False,
        "refresh_interval_ms": 2000,
        "use_friendly_names": True
    }
}

class ConfigManager:
    def __init__(self, config_path=None):
        if not config_path:
            user_config_dir = os.path.expanduser("~/.config/zerofreeze")
            user_config_file = os.path.join(user_config_dir, "config.json")
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            local_config_file = os.path.join(base_dir, "config.json")

            if os.path.exists(user_config_file):
                config_path = user_config_file
            elif os.access(base_dir, os.W_OK) and os.path.exists(local_config_file):
                config_path = local_config_file
            else:
                os.makedirs(user_config_dir, exist_ok=True)
                config_path = user_config_file
        self.config_path = config_path
        self.data = self.load()

    def load(self):
        if not os.path.exists(self.config_path):
            self.save(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Mescla chaves padrão ausentes
                merged = DEFAULT_CONFIG.copy()
                for section, vals in loaded.items():
                    if section in merged and isinstance(vals, dict):
                        merged[section].update(vals)
                    else:
                        merged[section] = vals
                return merged
        except Exception as e:
            print(f"[ZeroFreeze] Erro ao carregar config.json: {e}. Usando padrões.")
            return DEFAULT_CONFIG.copy()

    def save(self, data=None):
        if data:
            self.data = data
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ZeroFreeze] Erro ao salvar config.json: {e}")

    def get(self, section, key, default=None):
        return self.data.get(section, {}).get(key, default)

    def set(self, section, key, value):
        if section not in self.data:
            self.data[section] = {}
        self.data[section][key] = value
        self.save()
