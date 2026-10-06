#!/bin/bash
# Script de execução rápida do ZeroFreeze
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Previne abertura de múltiplas docks simultâneas
RUNNING_PID=$(pgrep -f "python3.*src/main.py" | grep -v "$$" | head -n 1)
if [ -n "$RUNNING_PID" ]; then
    echo "[ZeroFreeze] O aplicativo já está em execução no desktop (PID: $RUNNING_PID)."
    exit 0
fi

exec python3 src/main.py "$@"
