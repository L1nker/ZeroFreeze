"""
ZeroFreeze - Biblioteca de Nomes Amigáveis para Processos Linux
Traduz nomes técnicos de processos do sistema para nomes claros e entendíveis.
Inclui suporte a nomes truncados pelo kernel Linux (limite de 15 caracteres).
"""

FRIENDLY_NAMES = {

    # ============================================================
    # NAVEGADORES E SEUS SUBPROCESSOS
    # ============================================================
    "firefox":              "Mozilla Firefox",
    "firefox-bin":          "Mozilla Firefox",
    "firefox.":             "Mozilla Firefox",
    "isolated web co":      "Aba do Firefox",
    "webextensions":        "Extensão do Firefox",
    "WebExtensions":        "Extensão do Firefox",
    "privileged cont":      "Conteúdo Interno do Firefox",
    "Privileged Cont":      "Conteúdo Interno do Firefox",
    "socket process":       "Rede do Firefox",
    "Socket Process":       "Rede do Firefox",
    "rdd process":          "Decodificador de Mídia (Firefox)",
    "RDD Process":          "Decodificador de Mídia (Firefox)",
    "utility process":      "Processo Utilitário do Firefox",
    "Utility Process":      "Processo Utilitário do Firefox",
    "crashhelper":          "Reportador de Erros (Firefox)",
    "forkserver":           "Servidor de Processos (Firefox)",
    "chrome_crashpad":      "Monitor de Crashes (Brave/Chrome)",
    "brave":                "Brave Browser",
    "chrome":               "Google Chrome",
    "google-chrome":        "Google Chrome",
    "chromium":             "Chromium",
    "opera":                "Opera Browser",
    "msedge":               "Microsoft Edge",

    # ============================================================
    # EDITORES, IDEs E FERRAMENTAS DE DESENVOLVIMENTO
    # ============================================================
    "antigravity":          "Antigravity (Assistente de IA)",
    "antigravity-ide":      "Antigravity IDE",
    "code":                 "Visual Studio Code",
    "code-oss":             "VSCode (Open Source)",
    "sublime_text":         "Sublime Text",
    "pycharm":              "PyCharm IDE",
    "gedit":                "Editor de Texto (Gedit)",
    "gnome-text-edit":      "Editor de Texto (GNOME)",
    "gnome-text-editor":    "Editor de Texto (GNOME)",
    "language_server":      "Servidor de Linguagem (IDE)",
    "language_server_li":   "Servidor de Linguagem (IDE)",
    "pyrefly":              "Pyrefly LSP (Extensão IDE)",
    "google-drive-oc":      "Google Drive Sync",
    "google-drive-ocamlfuse": "Google Drive Sync",
    "npm":                  "Gerenciador de Pacotes Node.js (npm)",
    "node":                 "Ambiente Node.js",
    "python":               "Programa Python",
    "python3":              "Programa Python",
    "java":                 "Aplicação Java",

    # ============================================================
    # COMUNICAÇÃO E MÍDIA
    # ============================================================
    "discord":              "Discord",
    "spotify":              "Spotify",
    "telegram-desktop":     "Telegram",
    "telegram-deskto":      "Telegram",
    "slack":                "Slack",
    "vlc":                  "Reprodutor VLC",
    "rhythmbox":            "Reprodutor Rhythmbox",
    "steam":                "Steam (Jogos)",
    "copyq":                "Gerenciador de Área de Transferência (CopyQ)",

    # ============================================================
    # AMBIENTE GRÁFICO ZORIN OS / GNOME
    # ============================================================
    "gnome-shell":          "Interface Gráfica (Zorin OS)",
    "gnome-session-b":      "Sessão do Zorin OS (GNOME)",
    "gnome-session-binary": "Sessão do Zorin OS (GNOME)",
    "gnome-session-c":      "Controle da Sessão (GNOME)",
    "gnome-terminal":       "Terminal do Zorin",
    "gnome-terminal-":      "Terminal do Zorin",
    "gnome-terminal-server": "Terminal do Zorin",
    "gnome-terminal.":      "Terminal do Zorin",
    "gnome-shell-cal":      "Calendário da Barra Superior (GNOME)",
    "gnome-shell-calendar": "Calendário da Barra Superior (GNOME)",
    "gnome-software":       "Loja de Aplicativos do Zorin",
    "gnome-calendar":       "Calendário (GNOME)",
    "gnome-keyring-d":      "Porta-Chaves e Senhas (GNOME Keyring)",
    "gnome-keyring-daemon": "Porta-Chaves e Senhas (GNOME Keyring)",
    "gnome-remote-de":      "Área de Trabalho Remota (GNOME)",
    "gnome-remote-desktop": "Área de Trabalho Remota (GNOME)",
    "mutter":               "Compositor de Janelas (Mutter)",
    "mutter-x11-fram":      "Compositor Mutter em modo X11",
    "mutter-x11-frames":    "Compositor Mutter em modo X11",
    "cinnamon":             "Interface Gráfica (Linux Mint)",
    "xfwm4":                "Gerenciador de Janelas (XFCE)",
    "Xorg":                 "Servidor Gráfico (X11)",
    "wayland":              "Servidor Gráfico (Wayland)",
    "gdm3":                 "Gerenciador de Login (GDM)",
    "gdm-session-wor":      "Worker de Sessão do Login (GDM)",
    "gdm-session-worker":   "Worker de Sessão do Login (GDM)",
    "gdm-x-session":        "Sessão X11 do Login (GDM)",
    "gdm-wayland-session":  "Sessão Wayland do Login (GDM)",
    "lightdm":              "Gerenciador de Login (LightDM)",
    "gjs":                  "Script de Interface GNOME (GJS)",
    "nautilus":             "Gerenciador de Arquivos (Nautilus)",
    "nemo":                 "Gerenciador de Arquivos (Nemo)",
    "thunar":               "Gerenciador de Arquivos (Thunar)",

    # ============================================================
    # PORTAIS XDG (Integração Sistema / Flatpak)
    # ============================================================
    "xdg-desktop-por":      "Portal de Integração do Sistema (XDG)",
    "xdg-desktop-portal":   "Portal de Integração do Sistema (XDG)",
    "xdg-document-po":      "Portal de Documentos (XDG)",
    "xdg-document-portal":  "Portal de Documentos (XDG)",
    "xdg-permission-":      "Gerenciador de Permissões (XDG)",
    "xdg-permission-store": "Gerenciador de Permissões (XDG)",
    "xdg-dbus-proxy":       "Proxy de Comunicação D-Bus (Flatpak/XDG)",
    "xdg-open":             "Abridor de Arquivos Padrão (XDG)",
    "flatpak-session":      "Gerenciador de Sessão Flatpak",
    "fusermount3":          "Sistema de Arquivos Virtual (FUSE/Flatpak)",

    # ============================================================
    # CONFIGURAÇÕES DO GNOME/ZORIN (gsd-*)
    # ============================================================
    "gsd-a11y-settin":      "Configurações de Acessibilidade (Zorin)",
    "gsd-a11y-settings":    "Configurações de Acessibilidade (Zorin)",
    "gsd-color":            "Gerenciador de Cores e Calibração (Zorin)",
    "gsd-datetime":         "Configurações de Data e Hora (Zorin)",
    "gsd-disk-utilit":      "Monitor de Disco (Zorin)",
    "gsd-disk-utility-not": "Notificações de Disco (Zorin)",
    "gsd-housekeepin":      "Manutenção Automática do Sistema (Zorin)",
    "gsd-housekeeping":     "Manutenção Automática do Sistema (Zorin)",
    "gsd-keyboard":         "Configurações de Teclado (Zorin)",
    "gsd-media-keys":       "Teclas de Mídia e Atalhos (Zorin)",
    "gsd-power":            "Gerenciamento de Energia (Zorin)",
    "gsd-printer":          "Configurações de Impressora (Zorin)",
    "gsd-print-notif":      "Notificações de Impressão (Zorin)",
    "gsd-rfkill":           "Controle de Rádio Wi-Fi/Bluetooth (Zorin)",
    "gsd-screensaver":      "Protetor de Tela (Zorin)",
    "gsd-sharing":          "Compartilhamento de Arquivos (Zorin)",
    "gsd-smartcard":        "Leitor de Cartão Inteligente (Zorin)",
    "gsd-sound":            "Configurações de Som (Zorin)",
    "gsd-wacom":            "Suporte a Tablet Wacom (Zorin)",
    "gsd-xsettings":        "Configurações do Ambiente Gráfico (Zorin)",

    # ============================================================
    # INTEGRAÇÃO COM CONTAS E DADOS (EVOLUTION / GOA)
    # ============================================================
    "evolution-addre":      "Agenda de Contatos (GNOME)",
    "evolution-addressbook-factory": "Agenda de Contatos (GNOME)",
    "evolution-alarm":      "Notificações de Calendário (GNOME)",
    "evolution-alarm-notify": "Notificações de Calendário (GNOME)",
    "evolution-calen":      "Calendário (GNOME)",
    "evolution-calendar-factory": "Calendário (GNOME)",
    "evolution-sourc":      "Registro de Fontes de Dados (GNOME)",
    "evolution-source-registry": "Registro de Fontes de Dados (GNOME)",
    "goa-daemon":           "Contas Online do GNOME (GOA)",
    "goa-identity-se":      "Autenticação de Contas Online (GOA)",
    "goa-identity-service": "Autenticação de Contas Online (GOA)",
    "tracker-miner-f":      "Indexador de Arquivos (Tracker)",
    "tracker-miner-fs":     "Indexador de Arquivos (Tracker)",
    "dconf-service":        "Serviço de Configurações (DConf)",

    # ============================================================
    # SERVIÇOS DE FUNDO E DAEMONS DO LINUX
    # ============================================================
    "systemd":              "Sistema Central (Systemd)",
    "systemd-journald":     "Gerenciador de Logs do Sistema (Journal)",
    "systemd-udevd":        "Detector de Dispositivos de Hardware (Udev)",
    "systemd-resolved":     "Resolução de Nomes DNS (Systemd)",
    "systemd-timesyncd":    "Sincronização de Horário (Systemd)",
    "systemd-logind":       "Gerenciador de Sessões de Usuário",
    "systemd-oomd":         "Protetor de Memória do Sistema (OOMD)",
    "(sd-pam)":             "Módulo de Autenticação (PAM)",
    "NetworkManager":       "Gerenciador de Redes (Wi-Fi/Cabo)",
    "ModemManager":         "Gerenciador de Modem Móvel",
    "modem-daemon":         "Serviço de Modem",
    "wpa_supplicant":       "Gerenciador de Autenticação Wi-Fi (WPA)",
    "accounts-daemon":      "Gerenciador de Contas do Sistema",
    "bluetoothd":           "Serviço de Bluetooth",
    "colord":               "Gerenciador de Cores de Monitores",
    "boltd":                "Gerenciador de Dispositivos Thunderbolt",
    "avahi-daemon":         "Descoberta de Dispositivos na Rede (Avahi)",
    "pulseaudio":           "Servidor de Áudio (PulseAudio)",
    "pipewire":             "Servidor de Áudio/Vídeo (PipeWire)",
    "pipewire-pulse":       "Compatibilidade PulseAudio (PipeWire)",
    "wireplumber":          "Gerenciador de Sessão de Áudio (WirePlumber)",
    "callaudiod":           "Serviço de Áudio para Chamadas",
    "polkitd":              "Serviço de Autorizações (Polkit)",
    "dbus-daemon":          "Barramento de Comunicação do Sistema (D-Bus)",
    "upowerd":              "Gerenciador de Energia e Bateria",
    "rtkit-daemon":         "Escalonador de Áudio em Tempo Real (RTKit)",
    "at-spi2-registr":      "Registro de Acessibilidade (AT-SPI)",
    "at-spi2-registryd":    "Registro de Acessibilidade (AT-SPI)",
    "at-spi-bus-laun":      "Serviço de Acessibilidade (AT-SPI)",
    "at-spi-bus-launcher":  "Serviço de Acessibilidade (AT-SPI)",
    "packagekitd":          "Gerenciador de Pacotes e Atualizações",
    "unattended-upgr":      "Atualizações Automáticas de Segurança",
    "unattended-upgrades":  "Atualizações Automáticas de Segurança",
    "update-notifier":      "Notificador de Atualizações Disponíveis",
    "snapd":                "Gerenciador de Aplicativos Snap",
    "fwupd":                "Atualizador de Firmware de Hardware",
    "udisksd":              "Gerenciador de Discos e Partições (UDisks)",
    "thermald":             "Gerenciador Térmico do Processador",
    "power-profiles-":      "Perfis de Energia do Sistema",
    "power-profiles-daemon": "Perfis de Energia do Sistema",
    "switcheroo-cont":      "Controlador de GPU Integrada/Dedicada",
    "switcheroo-control":   "Controlador de GPU Integrada/Dedicada",
    "touchegg":             "Suporte a Gestos por Toque na Tela (Touchegg)",
    "rsyslogd":             "Registro de Logs do Sistema (Syslog)",
    "cron":                 "Agendador de Tarefas (Cron)",
    "cups-browsed":         "Descoberta de Impressoras na Rede (CUPS)",
    "cupsd":                "Servidor de Impressão (CUPS)",
    "firewall":             "Firewall do Sistema",
    "p11-kit-server":       "Servidor de Criptografia PKCS#11",
    "gcr-ssh-agent":        "Agente SSH (GNOME Keyring)",
    "psimon":               "Monitor de Processos do Sistema",
    "fctsched":             "Agendador de Tarefas em Tempo Real",

    # ============================================================
    # IA LOCAL E FERRAMENTAS
    # ============================================================
    "ollama":               "Servidor de IA Local (Ollama)",

    # ============================================================
    # VPN E SEGURANÇA
    # ============================================================
    "confighandler":        "FortiClient VPN",
    "forticlient":          "FortiClient VPN",
    "fortitray":            "FortiClient VPN (Bandeja do Sistema)",
    "fortitraylaunch":      "FortiClient VPN (Iniciador)",

    # ============================================================
    # SERVIDORES DE DESENVOLVIMENTO E BANCOS DE DADOS
    # ============================================================
    "docker":               "Docker (Containers)",
    "dockerd":              "Serviço do Docker",
    "containerd":           "Motor de Containers",
    "mysqld":               "Banco de Dados MySQL",
    "mariadbd":             "Banco de Dados MariaDB",
    "postgres":             "Banco de Dados PostgreSQL",
    "redis-server":         "Banco de Dados Redis",
    "nginx":                "Servidor Web Nginx",
    "apache2":              "Servidor Web Apache",

    # ============================================================
    # O PRÓPRIO ZEROFREEZE
    # ============================================================
    "ZeroFreeze":           "ZeroFreeze (Proteção Anti-Travamento)",
    "zerofreeze":           "ZeroFreeze (Proteção Anti-Travamento)",
}


# Nomes de processos "filhos" do Firefox que podem aparecer como raiz
_FIREFOX_CHILD_NAMES = {
    "firefox-bin", "isolated web co", "webextensions", "WebExtensions",
    "privileged cont", "Privileged Cont", "socket process", "Socket Process",
    "rdd process", "RDD Process", "utility process", "Utility Process",
    "crashhelper", "forkserver", "MainThread",
}


def resolve_friendly_name(raw_name, cmdline=None, children=None):
    """
    Traduz o nome técnico de um processo para um nome amigável e legível.

    Ordem de resolução:
    1. Detecta apps dentro do sandbox Flatpak (bwrap).
    2. Tenta match exato no dicionário.
    3. Tenta match em minúsculas.
    4. Trata threads/processos filhos conhecidos do Firefox como "Mozilla Firefox".
    5. Trata padrões 'gsd-*' como serviços do Zorin.
    6. Trata threads do kernel ([kworker], [migration], etc.).
    7. Trata scripts Python/Node identificando o nome do script.
    8. Fallback: retorna o nome original com primeira letra maiúscula.
    """
    clean_raw = raw_name.strip() if raw_name else "desconhecido"
    clean_lower = clean_raw.lower()

    # 1. Sandbox Flatpak (bwrap, --args bwrap, etc.)
    if "bwrap" in clean_lower or "bwap" in clean_lower or clean_lower.startswith("--args"):
        # Investiga filhos para identificar o app real
        if children:
            for child in children:
                c_name = (child.get("name") or "").lower()
                for key in ["firefox", "brave", "chrome", "steam", "discord", "spotify", "telegram"]:
                    if key in c_name:
                        return f"{FRIENDLY_NAMES.get(key, key.capitalize())} (Flatpak)"
        # Investiga o cmdline do próprio bwrap
        if cmdline:
            cmd_full = " ".join(cmdline).lower()
            for key in ["firefox", "brave", "chrome", "steam", "discord", "spotify", "telegram"]:
                if key in cmd_full:
                    return f"{FRIENDLY_NAMES.get(key, key.capitalize())} (Flatpak)"
        return "Aplicativo Isolado (Flatpak)"

    # 2. Match exato
    if clean_raw in FRIENDLY_NAMES:
        return FRIENDLY_NAMES[clean_raw]

    # 3. Match em minúsculas
    if clean_lower in FRIENDLY_NAMES:
        return FRIENDLY_NAMES[clean_lower]

    # 4. Threads/filhos do Firefox que aparecem como raiz
    if clean_raw in _FIREFOX_CHILD_NAMES or clean_lower in {n.lower() for n in _FIREFOX_CHILD_NAMES}:
        return "Mozilla Firefox"

    # 5. Threads do kernel Linux (aparecem entre colchetes)
    if clean_raw.startswith("[") and clean_raw.endswith("]"):
        inner = clean_raw[1:-1]
        if any(k in inner for k in ["kworker", "kthread"]):
            return "Tarefa de Manutenção do Kernel"
        if any(k in inner for k in ["migration", "cpuhp", "idle_inject"]):
            return "Balanceamento de Carga do Processador"
        if "btrfs" in inner:
            return "Manutenção do Sistema de Arquivos (Btrfs)"
        if "oom" in inner:
            return "Protetor de Memória (OOM Killer)"
        return f"Tarefa Interna do Kernel ({inner})"

    # 6. Processos 'gsd-*' (GNOME Settings Daemons)
    if clean_lower.startswith("gsd-"):
        part = clean_lower.replace("gsd-", "").replace("-", " ").capitalize()
        return f"Configurações de {part} (Zorin)"

    # 7. Scripts Python / Node / Electron — identifica pelo nome do script
    if clean_lower in ["python", "python3", "node", "electron"]:
        if cmdline and len(cmdline) > 1:
            import os
            for arg in cmdline[1:]:
                if not arg.startswith("-") and not arg.endswith(".pyc"):
                    base = os.path.basename(arg)
                    if base and "." in base:
                        return f"{base} (Python)" if "python" in clean_lower else f"{base} (Node)"
                    elif base:
                        return f"{base} ({clean_lower})"

    # 8. Fallback: capitaliza e retorna o nome original
    return clean_raw if clean_raw[0].isupper() else clean_raw.capitalize()
