"""
ZeroFreeze - Módulo de Histórico de Intervenções e Picos de Consumo
Registra salvamentos, alertas e processos que subiram de consumo repentinamente.
"""

import os
import json
import time
from datetime import datetime

CONFIG_DIR = os.path.expanduser("~/.config/ZeroFreeze")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.json")

def _ensure_dir():
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception:
        pass

def get_history_events(limit=50):
    """Retorna os eventos registrados mais recentes (do mais novo para o mais antigo)."""
    _ensure_dir()
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data[-limit:][::-1]
    except Exception as e:
        print(f"[ZeroFreeze] Erro ao ler histórico: {e}")
    return []

def add_history_event(event_type, app_name, memory_mb, percent, details=""):
    """
    Registra um novo evento no histórico.
    event_type: 'KILL' (Encerramento), 'ALERT' (Alerta 90%), 'SPIKE' (Pico repentino)
    """
    _ensure_dir()
    events = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                events = json.load(f)
                if not isinstance(events, list):
                    events = []
        except Exception:
            events = []

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    event = {
        "timestamp": now_str,
        "type": event_type,
        "app_name": app_name,
        "memory_mb": round(float(memory_mb), 1),
        "percent": round(float(percent), 1),
        "details": details
    }

    events.append(event)
    # Limita aos últimos 150 registros
    if len(events) > 150:
        events = events[-150:]

    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ZeroFreeze] Erro ao gravar evento no histórico: {e}")

def clear_history():
    """Limpa todo o histórico de eventos."""
    _ensure_dir()
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return True
    except Exception:
        return False
