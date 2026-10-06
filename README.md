# ❄️ ZeroFreeze — Gerenciador Inteligente de Memória & Widget de Monitoramento

O **ZeroFreeze** é um utilitário nativo e ultra-leve para Linux (com foco em **Zorin OS** e **Linux Mint**), projetado para erradicar os travamentos e congelamentos do sistema causados por saturação de memória RAM, além de fornecer um widget moderno e discreto na borda da tela.

- **Diretório de Desenvolvimento:** `/home/linker/AG_Local/ZeroFreeze` (executado localmente em disco rápido para estabilidade total de I/O e sem conflitos de sincronização).
- **Espelhamento de Documentação/Backup:** `AG_Projects/ZeroFreeze`

---

## 🎯 Conceito Central & Salvaguarda Anti-Freeze

Diferente de sistemas como o Windows que realizam gerenciamento agressivo de paging e compressão de memória, o Linux, por padrão, costuma entrar em *thrashing* (congelamento severo de I/O e swap) antes que o kernel OOM Killer entre em ação. 

O **ZeroFreeze** atua preventivamente em nível de usuário:
1. **Agrupamento por Árvore de Processos (Processo-Pai / Aplicação):**
   - Softwares modernos como Firefox, Chrome, Brave, VSCode e apps Electron fragmentam sua execução em dezenas de subprocessos (renderers, GPU, sandbox, network).
   - O ZeroFreeze agrupa de forma inteligente todos os subprocessos sob o **processo-pai/aplicação raiz**, somando os consumos de RAM e CPU.
   - Isso garante que o usuário veja apenas **uma entrada limpa e real** por aplicativo (ex: *"Firefox"* exibindo a soma real de todas as abas), sem poluição de subprocessos repetidos.
2. **Monitoramento em Tempo Real:** Varredura leve dos processos e consumo de hardware sem sobrecarregar a máquina.
3. **Alerta Sonoro Preventivo (90% de RAM):** Emite um bip/aviso sutil quando a memória atinge 90%, alertando o usuário antes de qualquer perigo.
4. **Salvaguarda Automática Anti-Travamento (98% de RAM):** Se o consumo atingir a linha crítica de 98%, o ZeroFreeze identifica a aplicação nº 1 mais pesada do ranking e encerra cirurgicamente o processo-pai (finalizando toda a árvore de subprocessos com segurança), salvando o sistema operacional de travar.
5. **Autopreservação Garantida:** O ZeroFreeze é imune a si mesmo e nunca encerrará seus próprios processos sob nenhuma circunstância.
6. **Lista Branca (Whitelist):** Permite cadastrar programas e serviços que nunca devem ser finalizados automaticamente (ex: componentes da interface gráfica, navegadores em trabalho crítico, etc.).

---

## 🎨 Interface Gráfica & Widget Lateral (Dock Auto-Hide)

Inspirado em interfaces orgânicas e minimalistas:
- **Design Retrátil (Auto-Hide):** Permanece oculto na borda da tela, deixando apenas uma aba sutil. O usuário escolhe se a abertura ocorre ao **passar o mouse (hover)** ou ao **clicar** na aba.
- **Posicionamento nos 4 Lados:** O usuário pode fixar o widget no **Topo**, **Chão/Fundo**, **Esquerda** ou **Direita**.
- **Controle de Deslocamento/Altura (Slider 0% a 100%):**
  - **Topo ou Chão:** `0%` = Esquerda | `50%` = Centro | `100%` = Direita.
  - **Laterais (Esquerda/Direita):** `0%` = Topo | `50%` = Centro | `100%` = Chão.
- **Medidores Radiais Circulares:**
  - **Memória RAM:** Anel colorido com porcentagem e alerta visual ao atingir zonas de risco.
  - **Processador (CPU):** Anel com taxa de utilização em tempo real.
  - **Armazenamentos Dinâmicos:** Detecta automaticamente todos os discos e partições instalados no PC e cria um controle circular para cada unidade.

---

## 🔍 Pop-ups Flutuantes com Detalhes (Flyout Cards)

Ao clicar em qualquer medidor circular, abre-se um balão com fundo escuro semi-transparente apontando para o controle selecionado:
- **Pop-up de Memória:**
  - Ranking das **5 aplicações mais gastonas** em RAM (consumo consolidado em MB/GB e %).
  - Botão opcional ao lado de cada aplicação para fechá-la manualmente (vem desativado por padrão, ativável nas configurações).
- **Pop-up de Processador (CPU):**
  - Ranking das **5 aplicações mais pesadas** em uso de CPU, ordenadas do maior para o menor.
- **Pop-up de Armazenamentos:**
  - Espaço total, ocupado e livre por unidade.
  - Velocidades de leitura e escrita em tempo real.
  - Diagnóstico de integridade/saúde do disco (SMART).

---

## ⚙️ Arquitetura Técnica & Compatibilidade

- **Linguagem & Framework:** Python 3 + PyGObject (GTK 3/4) + Cairo (desenho dos anéis vetoriais).
- **Consumo:** Extremamente frugal (< 30 MB de RAM).
- **Sessões Gráficas:**
  - **X11:** Compatibilidade nativa e total (100% estável no Zorin OS e Linux Mint).
  - **Wayland:** Suporte planejado via camadas `gtk-layer-shell`.
- **Serviço de Inicialização:** Inicia com o sistema através de `systemd --user` ou inicialização automática da sessão XDG.
