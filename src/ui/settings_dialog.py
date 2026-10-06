"""
ZeroFreeze - Painel Gráfico de Configurações
Interface moderna estruturada em 4 categorias (Exibição, Aparência, Módulos, Comportamento & Alertas)
com design inspirado no GNOME Settings / Adwaita.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango

from src.ui.color_picker import ScreenEyedropper
from src.ui.whitelist_dialog import WhitelistDialog
from src.ui.history_dialog import HistoryDialog
from src.autostart import is_autostart_enabled, set_autostart


class PreferencesRow(Gtk.Box):
    """
    Linha padronizada de preferência:
    - Título e subtítulo explicativo alinhados à esquerda.
    - Widget de controle (switch, combo, scale, botão) alinhado à direita.
    """
    def __init__(self, title, subtitle=None, control_widget=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(12)
        self.set_margin_end(12)

        # Caixa textual (Esquerda)
        box_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box_text.set_hexpand(True)
        box_text.set_valign(Gtk.Align.CENTER)

        lbl_title = Gtk.Label()
        lbl_title.set_markup(f"<b>{title}</b>")
        lbl_title.set_halign(Gtk.Align.START)
        box_text.pack_start(lbl_title, False, False, 0)

        if subtitle:
            lbl_sub = Gtk.Label()
            lbl_sub.set_markup(f"<small>{subtitle}</small>")
            lbl_sub.set_halign(Gtk.Align.START)
            lbl_sub.set_line_wrap(True)
            lbl_sub.get_style_context().add_class("dim-label")
            box_text.pack_start(lbl_sub, False, False, 0)

        self.pack_start(box_text, True, True, 0)

        # Widget de Controle (Direita)
        if control_widget:
            control_widget.set_valign(Gtk.Align.CENTER)
            self.pack_end(control_widget, False, False, 0)


class PreferencesGroup(Gtk.Frame):
    """
    Grupo de preferências estilo Adwaita/Card com cantos arredondados,
    contendo múltiplas PreferencesRow separadas sutilmente.
    """
    def __init__(self, title=None):
        super().__init__()
        self.set_shadow_type(Gtk.ShadowType.IN)
        self.get_style_context().add_class("view")
        self.get_style_context().add_class("pref-group-card")

        self.box_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.box_content.set_margin_top(4)
        self.box_content.set_margin_bottom(4)
        self.add(self.box_content)

        self.title = title

    def add_row(self, row_widget):
        if len(self.box_content.get_children()) > 0:
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            sep.set_margin_start(10)
            sep.set_margin_end(10)
            self.box_content.pack_start(sep, False, False, 0)
        self.box_content.pack_start(row_widget, False, False, 0)


class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent, config_manager, on_settings_changed_callback=None, monitor=None):
        super().__init__(
            title="⚙️ Configurações do ZeroFreeze",
            parent=parent,
            flags=0
        )
        self.config_mgr = config_manager
        self.on_changed = on_settings_changed_callback
        self.monitor = monitor or getattr(parent, 'monitor', None)
        self._is_loading = True
        self._is_destroying = False
        self.connect("destroy", self._on_dialog_destroy)

        self.set_default_size(580, 640)
        self.set_resizable(True)

        self._apply_custom_css()

        self.add_button("Concluído", Gtk.ResponseType.OK)

        # Cabeçalho da janela com seletor de abas moderno
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header_box.set_margin_top(8)
        header_box.set_margin_bottom(4)
        header_box.set_margin_start(16)
        header_box.set_margin_end(16)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_halign(Gtk.Align.CENTER)
        header_box.pack_start(switcher, False, False, 0)

        content_area = self.get_content_area()
        content_area.pack_start(header_box, False, False, 0)
        content_area.pack_start(self.stack, True, True, 0)

        # Construção das 4 Abas
        self._build_tab_display()
        self._build_tab_appearance()
        self._build_tab_modules()
        self._build_tab_system()

        # Desativa a captura indesejada de rolagem do mouse em sliders e combos
        self._disable_scroll_recursively(content_area)

        # Conectar todos os gatilhos em tempo real (Live Change)
        self._connect_live_signals()

        self._is_loading = False
        self.show_all()
        self._update_notch_visibility()

    def _apply_custom_css(self):
        """Aplica estilos CSS sutis para cartões e aparência moderna tipo Adwaita."""
        css = b"""
        .pref-group-card {
            background-color: alpha(@theme_base_color, 0.5);
            border-radius: 10px;
            border: 1px solid alpha(@borders, 0.4);
            margin: 6px 12px 14px 12px;
        }
        .pref-section-title {
            font-size: 11pt;
            font-weight: bold;
            margin: 12px 14px 4px 14px;
        }
        button.color {
            padding: 0px;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.25);
            min-width: 44px;
            min-height: 26px;
            background: transparent;
            box-shadow: none;
        }
        button.color colorswatch:only-child,
        button.color colorswatch:only-child overlay {
            border-radius: 5px;
            margin: 0px;
            padding: 0px;
            border: none;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # =========================================================================
    # ABA 1: EXIBIÇÃO (MONITOR, ALINHAMENTO E COMPORTAMENTO DA DOCK)
    # =========================================================================
    def _build_tab_display(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box_page.set_margin_top(8)
        box_page.set_margin_bottom(12)
        scrolled.add(box_page)

        # --- Grupo 1: Tela & Posicionamento ---
        lbl_sec1 = Gtk.Label(label="Monitor e Alinhamento")
        lbl_sec1.set_halign(Gtk.Align.START)
        lbl_sec1.get_style_context().add_class("pref-section-title")
        box_page.pack_start(lbl_sec1, False, False, 0)

        group_pos = PreferencesGroup()

        # Monitor
        self.combo_mon = Gtk.ComboBoxText()
        self.combo_mon.append("primary", "⭐ Tela Principal")
        display = Gdk.Display.get_default()
        for i in range(display.get_n_monitors()):
            m = display.get_monitor(i)
            g = m.get_geometry()
            model = m.get_model() or f"Monitor {i+1}"
            tag = " [Principal]" if m.is_primary() else ""
            self.combo_mon.append(str(i), f"Monitor {i+1} ({model} - {g.width}x{g.height}){tag}")
        curr_target = str(self.config_mgr.get("dock", "target_monitor", "primary"))
        self.combo_mon.set_active_id(curr_target)

        row_mon = PreferencesRow(
            title="Monitor de Exibição",
            subtitle="Selecione o monitor onde a dock ficará fixada",
            control_widget=self.combo_mon
        )
        group_pos.add_row(row_mon)

        # Borda da Tela
        self.combo_edge = Gtk.ComboBoxText()
        self.combo_edge.append("right", "Borda Direita")
        self.combo_edge.append("left", "Borda Esquerda")
        curr_edge = self.config_mgr.get("dock", "edge", "right")
        if curr_edge not in ["right", "left"]:
            curr_edge = "right"
        self.combo_edge.set_active_id(curr_edge)

        row_edge = PreferencesRow(
            title="Lado da Tela",
            subtitle="Escolha em qual borda vertical ancorar a ferramenta",
            control_widget=self.combo_edge
        )
        group_pos.add_row(row_edge)

        # Posição do Widget (Slider com formatação %)
        curr_offset = self.config_mgr.get("dock", "offset_percent", 50)
        self.adj_offset = Gtk.Adjustment(value=curr_offset, lower=-50, upper=150, step_increment=1, page_increment=10)
        self.scale_offset = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adj_offset)
        self.scale_offset.set_size_request(160, -1)
        self.scale_offset.set_digits(0)
        self.scale_offset.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_offset.connect(
            "format-value",
            lambda s, val: f"{max(0, min(100, int(round((val - (-50)) / (150 - (-50)) * 100))))}%"
        )

        row_offset = PreferencesRow(
            title="Posição do Widget",
            subtitle="Ajuste a altura da dock ao longo da borda selecionada",
            control_widget=self.scale_offset
        )
        group_pos.add_row(row_offset)
        box_page.pack_start(group_pos, False, False, 0)

        # --- Grupo 2: Comportamento da Barra (Movido da antiga aba Comportamento para cá) ---
        lbl_sec_dock = Gtk.Label(label="Comportamento da Dock")
        lbl_sec_dock.set_halign(Gtk.Align.START)
        lbl_sec_dock.get_style_context().add_class("pref-section-title")
        box_page.pack_start(lbl_sec_dock, False, False, 0)

        group_dock = PreferencesGroup()

        # Auto-Hide
        self.switch_autohide = Gtk.Switch()
        self.switch_autohide.set_active(self.config_mgr.get("dock", "auto_hide", True))
        row_autohide = PreferencesRow(
            title="Auto-Hide",
            subtitle="Recolhe a barra na borda quando o cursor não estiver sobre ela",
            control_widget=self.switch_autohide
        )
        group_dock.add_row(row_autohide)

        # Entalhe Luminoso (Notch)
        box_notch_ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box_notch_ctrl.set_valign(Gtk.Align.CENTER)
        self.switch_notch = Gtk.Switch()
        self.switch_notch.set_valign(Gtk.Align.CENTER)
        self.switch_notch.set_active(self.config_mgr.get("dock", "notch_enabled", True))
        box_notch_ctrl.pack_start(self.switch_notch, False, False, 0)

        notch_c = self.config_mgr.get("colors", "notch_color", [0.0, 0.28, 1.0])
        self.btn_notch_color = Gtk.ColorButton()
        self.btn_notch_color.set_valign(Gtk.Align.CENTER)
        self.btn_notch_color.set_rgba(Gdk.RGBA(notch_c[0], notch_c[1], notch_c[2], 1.0))
        self.btn_notch_color.set_tooltip_text("Cor da barrinha luminosa de guia (entalhe)")
        box_notch_ctrl.pack_start(self.btn_notch_color, False, False, 0)

        self.row_notch = PreferencesRow(
            title="Entalhe Luminoso",
            subtitle="Barrinha sutil na borda para localizar a dock recolhida e escolher a cor",
            control_widget=box_notch_ctrl
        )
        group_dock.add_row(self.row_notch)

        # Modo de Abertura
        self.combo_trigger = Gtk.ComboBoxText()
        self.combo_trigger.append("hover", "Passar o mouse (Hover)")
        self.combo_trigger.append("click", "Clicar na abinha")
        self.combo_trigger.set_active_id(self.config_mgr.get("dock", "trigger_mode", "hover"))
        row_trig = PreferencesRow(
            title="Abrir Dock ao",
            subtitle="Escolha como revelar a dock quando estiver escondida",
            control_widget=self.combo_trigger
        )
        group_dock.add_row(row_trig)

        box_page.pack_start(group_dock, False, False, 0)

        self.stack.add_titled(scrolled, "display", "Exibição")

    # =========================================================================
    # ABA 2: APARÊNCIA (FUNDO E DIMENSÕES / PROPORÇÕES)
    # =========================================================================
    def _build_tab_appearance(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box_page.set_margin_top(8)
        box_page.set_margin_bottom(12)
        scrolled.add(box_page)

        # --- Grupo 1: Fundo da Dock ---
        lbl_sec1 = Gtk.Label(label="Fundo da Barra")
        lbl_sec1.set_halign(Gtk.Align.START)
        lbl_sec1.get_style_context().add_class("pref-section-title")
        box_page.pack_start(lbl_sec1, False, False, 0)

        group_bg = PreferencesGroup()

        # Seletor de Cor + Conta-Gotas
        box_bg_ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cfg_r = self.config_mgr.get("colors", "background_r", 0.06)
        cfg_g = self.config_mgr.get("colors", "background_g", 0.07)
        cfg_b = self.config_mgr.get("colors", "background_b", 0.09)
        cfg_a = self.config_mgr.get("colors", "background_a", 0.94)

        self.btn_bg_color = Gtk.ColorButton()
        self.btn_bg_color.set_rgba(Gdk.RGBA(cfg_r, cfg_g, cfg_b, cfg_a))
        box_bg_ctrl.pack_start(self.btn_bg_color, False, False, 0)

        btn_picker = Gtk.Button(label="💉 Conta-gotas")
        btn_picker.set_tooltip_text("Capturar qualquer cor diretamente da tela (janela, papel de parede, barra)")
        btn_picker.connect("clicked", self._start_eyedropper)
        box_bg_ctrl.pack_start(btn_picker, False, False, 0)

        row_bg = PreferencesRow(
            title="Cor de Fundo",
            subtitle="Tonalidade da base da dock (clique no conta-gotas para copiar da tela)",
            control_widget=box_bg_ctrl
        )
        group_bg.add_row(row_bg)

        # Opacidade do Fundo
        self.adj_alpha = Gtk.Adjustment(value=int(cfg_a * 100), lower=20, upper=100, step_increment=1, page_increment=10)
        self.scale_alpha = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adj_alpha)
        self.scale_alpha.set_size_request(160, -1)
        self.scale_alpha.set_digits(0)
        self.scale_alpha.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_alpha.connect("format-value", lambda s, val: f"{int(val)}%")

        row_alpha = PreferencesRow(
            title="Opacidade do Fundo",
            subtitle="Nível de transparência da barra lateral",
            control_widget=self.scale_alpha
        )
        group_bg.add_row(row_alpha)
        box_page.pack_start(group_bg, False, False, 0)

        # --- Grupo 2: Dimensões Visuais (Movido de Exibição para cá) ---
        lbl_sec2 = Gtk.Label(label="Dimensões e Proporções")
        lbl_sec2.set_halign(Gtk.Align.START)
        lbl_sec2.get_style_context().add_class("pref-section-title")
        box_page.pack_start(lbl_sec2, False, False, 0)

        group_dim = PreferencesGroup()

        # Tamanho do Widget (Scale 33 a 100)
        curr_scale = self.config_mgr.get("dock", "scale_percent", 100)
        self.adj_scale = Gtk.Adjustment(value=curr_scale, lower=33, upper=100, step_increment=1, page_increment=10)
        self.scale_size = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adj_scale)
        self.scale_size.set_size_request(160, -1)
        self.scale_size.set_digits(0)
        self.scale_size.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_size.connect(
            "format-value",
            lambda s, val: f"{max(0, min(100, int(round((val - 33) / (100 - 33) * 100))))}%"
        )
        row_size = PreferencesRow(
            title="Tamanho do Widget",
            subtitle="Escala geral de visualização da dock e medidores",
            control_widget=self.scale_size
        )
        group_dim.add_row(row_size)

        # Distância entre os Elementos (-10 a 60)
        curr_spacing = self.config_mgr.get("dock", "element_spacing", 8)
        self.adj_spacing = Gtk.Adjustment(value=curr_spacing, lower=-10, upper=60, step_increment=1, page_increment=5)
        self.scale_spacing = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adj_spacing)
        self.scale_spacing.set_size_request(160, -1)
        self.scale_spacing.set_digits(0)
        self.scale_spacing.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_spacing.connect(
            "format-value",
            lambda s, val: f"{max(0, min(100, int(round((val - (-10)) / (60 - (-10)) * 100))))}%"
        )
        row_spacing = PreferencesRow(
            title="Distância entre os Elementos",
            subtitle="Espaçamento vertical entre os 3 anéis circulares",
            control_widget=self.scale_spacing
        )
        group_dim.add_row(row_spacing)

        # Tamanho da Dock (Base retangular central: 0 a 300)
        curr_base_mid = self.config_mgr.get("dock", "base_middle_height", 140)
        self.adj_base_mid = Gtk.Adjustment(value=curr_base_mid, lower=0, upper=300, step_increment=1, page_increment=10)
        self.scale_base_middle = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adj_base_mid)
        self.scale_base_middle.set_size_request(160, -1)
        self.scale_base_middle.set_digits(0)
        self.scale_base_middle.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale_base_middle.connect(
            "format-value",
            lambda s, val: f"{max(0, min(100, int(round((val - 0) / (300 - 0) * 100))))}%"
        )
        row_base = PreferencesRow(
            title="Tamanho da Dock",
            subtitle="Comprimento da base de apoio retangular",
            control_widget=self.scale_base_middle
        )
        group_dim.add_row(row_base)
        box_page.pack_start(group_dim, False, False, 0)

        self.stack.add_titled(scrolled, "appearance", "Aparência")

    # =========================================================================
    # ABA 3: MÓDULOS (ORDEM DOS MEDIDORES E CORES DOS ÍCONES)
    # =========================================================================
    def _build_tab_modules(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box_page.set_margin_top(8)
        box_page.set_margin_bottom(12)
        scrolled.add(box_page)

        # --- Grupo 1: Ordem dos Medidores ---
        lbl_sec = Gtk.Label(label="Organização dos Medidores")
        lbl_sec.set_halign(Gtk.Align.START)
        lbl_sec.get_style_context().add_class("pref-section-title")
        box_page.pack_start(lbl_sec, False, False, 0)

        self.element_order = list(self.config_mgr.get("dock", "element_order", ["ram", "cpu", "storage"]))
        for k in ["ram", "cpu", "storage"]:
            if k not in self.element_order:
                self.element_order.append(k)

        self.group_order = PreferencesGroup()
        self.box_order_items = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.group_order.box_content.pack_start(self.box_order_items, True, True, 0)
        box_page.pack_start(self.group_order, False, False, 0)

        lbl_hint = Gtk.Label(
            label="Defina a sequência dos anéis na dock vertical (de cima para baixo).\n"
                  "Clique em 'Subir' ou 'Descer' para reorganizar a ordem visual."
        )
        lbl_hint.set_halign(Gtk.Align.START)
        lbl_hint.set_margin_start(16)
        lbl_hint.set_margin_end(16)
        lbl_hint.get_style_context().add_class("dim-label")
        box_page.pack_start(lbl_hint, False, False, 6)

        self._refresh_order_ui()

        # --- Grupo 2: Cores dos Ícones Centrais (Movido de Aparência para cá) ---
        lbl_sec2 = Gtk.Label(label="Cores dos Ícones Centrais")
        lbl_sec2.set_halign(Gtk.Align.START)
        lbl_sec2.get_style_context().add_class("pref-section-title")
        box_page.pack_start(lbl_sec2, False, False, 0)

        group_icons = PreferencesGroup()

        # RAM
        ram_c = self.config_mgr.get("colors", "ram_ring", [1.0, 0.45, 0.0])
        self.btn_ram_color = Gtk.ColorButton()
        self.btn_ram_color.set_rgba(Gdk.RGBA(ram_c[0], ram_c[1], ram_c[2], 1.0))
        row_ram = PreferencesRow(
            title="Ícone de Memória RAM",
            subtitle="Cor do símbolo central de memória",
            control_widget=self.btn_ram_color
        )
        group_icons.add_row(row_ram)

        # CPU
        cpu_c = self.config_mgr.get("colors", "cpu_ring", [0.15, 0.85, 0.55])
        self.btn_cpu_color = Gtk.ColorButton()
        self.btn_cpu_color.set_rgba(Gdk.RGBA(cpu_c[0], cpu_c[1], cpu_c[2], 1.0))
        row_cpu = PreferencesRow(
            title="Ícone de Processador (CPU)",
            subtitle="Cor do símbolo central do processador",
            control_widget=self.btn_cpu_color
        )
        group_icons.add_row(row_cpu)

        # Armazenamento
        disk_c = self.config_mgr.get("colors", "disk_ring", [0.95, 0.80, 0.15])
        self.btn_disk_color = Gtk.ColorButton()
        self.btn_disk_color.set_rgba(Gdk.RGBA(disk_c[0], disk_c[1], disk_c[2], 1.0))
        row_disk = PreferencesRow(
            title="Ícone de Armazenamento",
            subtitle="Cor do símbolo central de discos e partições",
            control_widget=self.btn_disk_color
        )
        group_icons.add_row(row_disk)

        box_page.pack_start(group_icons, False, False, 0)

        self.stack.add_titled(scrolled, "modules", "Módulos")

    def _refresh_order_ui(self):
        """Reconstrói os elementos do grupo de ordenação."""
        for child in list(self.box_order_items.get_children()):
            self.box_order_items.remove(child)

        labels_map = {
            "ram": ("⚡ Memória RAM", "Monitoramento em tempo real da memória física"),
            "cpu": ("✹ Processador (CPU)", "Uso instantâneo da CPU e núcleos"),
            "storage": ("💾 Armazenamento", "Espaço em disco e uso do sistema de arquivos")
        }

        for idx, key in enumerate(self.element_order):
            if idx > 0:
                sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                sep.set_margin_start(10)
                sep.set_margin_end(10)
                self.box_order_items.pack_start(sep, False, False, 0)

            title, sub = labels_map.get(key, (key, ""))

            box_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            btn_up = Gtk.Button(label="▲ Subir")
            btn_up.set_sensitive(idx > 0)
            btn_up.connect("clicked", lambda w, i=idx: self._move_order_item(i, -1))
            box_btns.pack_start(btn_up, False, False, 0)

            btn_down = Gtk.Button(label="▼ Descer")
            btn_down.set_sensitive(idx < len(self.element_order) - 1)
            btn_down.connect("clicked", lambda w, i=idx: self._move_order_item(i, 1))
            box_btns.pack_start(btn_down, False, False, 0)

            row = PreferencesRow(
                title=f"{idx + 1}º - {title}",
                subtitle=sub,
                control_widget=box_btns
            )
            self.box_order_items.pack_start(row, False, False, 0)

        self.box_order_items.show_all()

    def _move_order_item(self, idx, direction):
        new_idx = idx + direction
        if 0 <= new_idx < len(self.element_order):
            self.element_order[idx], self.element_order[new_idx] = self.element_order[new_idx], self.element_order[idx]
            self._refresh_order_ui()
            self._on_live_change()

    # =========================================================================
    # ABA 4: SISTEMA (INTEGRAÇÃO, SALVAGUARDA ANTI-FREEZE, WHITELIST E HISTÓRICO)
    # =========================================================================
    def _build_tab_system(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box_page.set_margin_top(8)
        box_page.set_margin_bottom(12)
        scrolled.add(box_page)

        # --- Grupo 1: Sistema e Inicialização ---
        lbl_sec_sys = Gtk.Label(label="Sistema & Integração")
        lbl_sec_sys.set_halign(Gtk.Align.START)
        lbl_sec_sys.get_style_context().add_class("pref-section-title")
        box_page.pack_start(lbl_sec_sys, False, False, 0)

        group_sys = PreferencesGroup()

        # Iniciar com o Sistema (Autostart)
        self.switch_autostart = Gtk.Switch()
        self.switch_autostart.set_active(is_autostart_enabled())
        self.switch_autostart.connect("notify::active", self._on_autostart_toggled)
        row_autostart = PreferencesRow(
            title="Iniciar com o Sistema",
            subtitle="Abrir o ZeroFreeze automaticamente ao ligar o computador",
            control_widget=self.switch_autostart
        )
        group_sys.add_row(row_autostart)

        # Frequência de Atualização
        self.combo_refresh = Gtk.ComboBoxText()
        self.combo_refresh.append("1000", "1 segundo (Mais ágil)")
        self.combo_refresh.append("2000", "2 segundos (Recomendado)")
        self.combo_refresh.append("3000", "3 segundos (Econômico)")
        self.combo_refresh.append("5000", "5 segundos")
        curr_refresh = str(self.config_mgr.get("ui", "refresh_interval_ms", 2000))
        self.combo_refresh.set_active_id(curr_refresh if curr_refresh in ["1000", "2000", "3000", "5000"] else "2000")
        row_refresh = PreferencesRow(
            title="Taxa de Leitura dos Dados",
            subtitle="Intervalo de consulta de memória, CPU e disco",
            control_widget=self.combo_refresh
        )
        group_sys.add_row(row_refresh)

        # Nomes Amigáveis
        self.switch_friendly = Gtk.Switch()
        self.switch_friendly.set_active(self.config_mgr.get("ui", "use_friendly_names", True))
        row_friendly = PreferencesRow(
            title="Nomes Amigáveis de Aplicativos",
            subtitle="Substitui nomes técnicos (ex: 'bwrap' por 'Mozilla Firefox')",
            control_widget=self.switch_friendly
        )
        group_sys.add_row(row_friendly)

        box_page.pack_start(group_sys, False, False, 0)

        # --- Grupo 2: Salvaguarda Anti-Travamento (RAM) ---
        lbl_sec_safe = Gtk.Label(label="Salvaguarda Anti-Travamento (Anti-Freeze)")
        lbl_sec_safe.set_halign(Gtk.Align.START)
        lbl_sec_safe.get_style_context().add_class("pref-section-title")
        box_page.pack_start(lbl_sec_safe, False, False, 0)

        group_safe = PreferencesGroup()

        # Alerta Preventivo (SpinButton)
        curr_sound_thresh = int(self.config_mgr.get("safety", "sound_threshold_percent", 90.0))
        self.adj_sound_thresh = Gtk.Adjustment(value=curr_sound_thresh, lower=50, upper=98, step_increment=1, page_increment=5)
        self.spin_sound_thresh = Gtk.SpinButton(adjustment=self.adj_sound_thresh, climb_rate=1, digits=0)
        self.spin_sound_thresh.set_numeric(True)
        row_sound_thresh = PreferencesRow(
            title="Gatilho 1: Alerta Preventivo (% RAM)",
            subtitle="Porcentagem de consumo para emitir notificação e aviso sonoro",
            control_widget=self.spin_sound_thresh
        )
        group_safe.add_row(row_sound_thresh)

        # Ataque / Encerramento do Vilão (SpinButton)
        curr_kill_thresh = int(self.config_mgr.get("safety", "kill_threshold_percent", 93.0))
        self.adj_kill_thresh = Gtk.Adjustment(value=curr_kill_thresh, lower=51, upper=99, step_increment=1, page_increment=5)
        self.spin_kill_thresh = Gtk.SpinButton(adjustment=self.adj_kill_thresh, climb_rate=1, digits=0)
        self.spin_kill_thresh.set_numeric(True)
        row_kill_thresh = PreferencesRow(
            title="Gatilho 2: Encerramento de Emergência (% RAM)",
            subtitle="Nível crítico onde o ZeroFreeze encerra cirurgicamente o processo vilão",
            control_widget=self.spin_kill_thresh
        )
        group_safe.add_row(row_kill_thresh)

        # Alerta Sonoro
        self.switch_sound = Gtk.Switch()
        self.switch_sound.set_active(self.config_mgr.get("safety", "sound_alert_enabled", True))
        row_sound = PreferencesRow(
            title="Aviso Sonoro de Emergência",
            subtitle="Toca um bipe sonoro quando a memória atingir níveis perigosos",
            control_widget=self.switch_sound
        )
        group_safe.add_row(row_sound)

        # Botões de Encerramento Manual nos Pop-ups
        self.switch_manual_kill = Gtk.Switch()
        self.switch_manual_kill.set_active(self.config_mgr.get("ui", "show_manual_kill_buttons", False))
        row_manual_kill = PreferencesRow(
            title="Botões de Fechamento Manual nos Pop-ups",
            subtitle="Adiciona um botão 'Encerrar' ao lado de cada app no detalhamento",
            control_widget=self.switch_manual_kill
        )
        group_safe.add_row(row_manual_kill)

        box_page.pack_start(group_safe, False, False, 0)

        # --- Grupo 3: Lista Branca e Histórico ---
        lbl_sec_tools = Gtk.Label(label="Proteção & Histórico de Intervenções")
        lbl_sec_tools.set_halign(Gtk.Align.START)
        lbl_sec_tools.get_style_context().add_class("pref-section-title")
        box_page.pack_start(lbl_sec_tools, False, False, 0)

        group_tools = PreferencesGroup()

        # Botão Lista Branca
        btn_whitelist = Gtk.Button(label="🛡️ Gerenciar Lista Branca...")
        btn_whitelist.connect("clicked", self._open_whitelist_dialog)
        row_whitelist = PreferencesRow(
            title="Lista Branca de Aplicativos",
            subtitle="Selecione quais programas nunca podem ser encerrados pelo sistema",
            control_widget=btn_whitelist
        )
        group_tools.add_row(row_whitelist)

        # Botão Histórico
        btn_history = Gtk.Button(label="📜 Histórico de Intervenções...")
        btn_history.connect("clicked", self._open_history_dialog)
        row_history = PreferencesRow(
            title="Histórico de Ações e Picos",
            subtitle="Veja quando a salvaguarda agiu, alertas emitidos e saltos de consumo",
            control_widget=btn_history
        )
        group_tools.add_row(row_history)

        box_page.pack_start(group_tools, False, False, 0)

        self.stack.add_titled(scrolled, "system", "Sistema")


    # =========================================================================
    # DIÁLOGOS AUXILIARES: LISTA BRANCA E HISTÓRICO
    # =========================================================================
    def _open_whitelist_dialog(self, widget):
        dlg = WhitelistDialog(
            parent=self,
            config_manager=self.config_mgr,
            monitor=self.monitor,
            on_changed_callback=self._on_live_change
        )
        dlg.run()
        dlg.destroy()

    def _open_history_dialog(self, widget):
        dlg = HistoryDialog(parent=self)
        dlg.run()
        dlg.destroy()

    def _on_autostart_toggled(self, switch, gparam):
        is_on = switch.get_active()
        set_autostart(is_on)

    # =========================================================================
    # CONEXÕES LIVE-UPDATE
    # =========================================================================
    def _connect_live_signals(self):
        # Exibição
        self.combo_mon.connect("changed", self._on_live_change)
        self.combo_edge.connect("changed", self._on_live_change)
        self.scale_offset.connect("value-changed", self._on_live_change)
        self.scale_size.connect("value-changed", self._on_live_change)
        self.scale_spacing.connect("value-changed", self._on_live_change)
        self.scale_base_middle.connect("value-changed", self._on_live_change)

        # Aparência
        self.btn_bg_color.connect("color-set", self._on_live_change)
        self.scale_alpha.connect("value-changed", self._on_live_change)
        self.btn_ram_color.connect("color-set", self._on_live_change)
        self.btn_cpu_color.connect("color-set", self._on_live_change)
        self.btn_disk_color.connect("color-set", self._on_live_change)

        # Comportamento
        self.switch_autohide.connect("notify::active", self._on_autohide_switched)
        self.switch_notch.connect("notify::active", self._on_notch_switched)
        self.btn_notch_color.connect("color-set", self._on_live_change)
        self.combo_trigger.connect("changed", self._on_live_change)
        self.combo_refresh.connect("changed", self._on_live_change)
        self.switch_friendly.connect("notify::active", self._on_live_change)
        self.spin_sound_thresh.connect("value-changed", self._on_live_change)
        self.spin_kill_thresh.connect("value-changed", self._on_live_change)
        self.switch_sound.connect("notify::active", self._on_live_change)
        self.switch_manual_kill.connect("notify::active", self._on_live_change)

    def _disable_scroll_recursively(self, widget):
        if isinstance(widget, (Gtk.ComboBox, Gtk.Scale, Gtk.SpinButton)):
            widget.connect("scroll-event", lambda w, e: True)
        if isinstance(widget, Gtk.Container):
            widget.foreach(self._disable_scroll_recursively)

    def _start_eyedropper(self, widget):
        def on_color_picked(r, g, b):
            if getattr(self, "_is_destroying", False):
                return
            alpha = self.scale_alpha.get_value() / 100.0
            self.btn_bg_color.set_rgba(Gdk.RGBA(r, g, b, alpha))
            self._on_live_change()

        ScreenEyedropper(on_color_picked, parent_window=self)

    def _update_notch_visibility(self):
        autohide_active = self.switch_autohide.get_active()
        self.row_notch.set_visible(autohide_active)
        notch_active = self.switch_notch.get_active()
        self.btn_notch_color.set_visible(autohide_active and notch_active)

    def _on_autohide_switched(self, switch, gparam):
        self._update_notch_visibility()
        self._on_live_change()

    def _on_notch_switched(self, switch, gparam):
        self._update_notch_visibility()
        self._on_live_change()

    def _on_dialog_destroy(self, *args):
        self._is_destroying = True

    def _on_live_change(self, *args):
        if getattr(self, "_is_loading", False) or getattr(self, "_is_destroying", False):
            return
        self.apply_settings()

    def apply_settings(self):
        if getattr(self, "_is_destroying", False):
            return
        target_mon = self.combo_mon.get_active_id() or "primary"
        edge = self.combo_edge.get_active_id() or "right"
        offset = int(self.scale_offset.get_value())
        auto_hide = self.switch_autohide.get_active()
        notch_enabled = self.switch_notch.get_active()
        notch_rgba = self.btn_notch_color.get_rgba()
        trigger = self.combo_trigger.get_active_id() or "hover"

        sound = self.switch_sound.get_active()
        sound_thresh = float(self.spin_sound_thresh.get_value())
        kill_thresh = float(self.spin_kill_thresh.get_value())
        if kill_thresh < sound_thresh:
            kill_thresh = sound_thresh
            self.spin_kill_thresh.set_value(kill_thresh)

        manual_kill = self.switch_manual_kill.get_active()
        friendly_names = self.switch_friendly.get_active()
        refresh_ms = int(self.combo_refresh.get_active_id() or "2000")

        # Cores
        bg_rgba = self.btn_bg_color.get_rgba()
        bg_a = self.scale_alpha.get_value() / 100.0
        ram_rgba = self.btn_ram_color.get_rgba()
        cpu_rgba = self.btn_cpu_color.get_rgba()
        disk_rgba = self.btn_disk_color.get_rgba()

        scale_pct = int(self.scale_size.get_value())
        spacing = int(self.scale_spacing.get_value())
        base_mid = int(self.scale_base_middle.get_value())

        self.config_mgr.set("dock", "target_monitor", target_mon)
        self.config_mgr.set("dock", "edge", edge)
        self.config_mgr.set("dock", "offset_percent", offset)
        self.config_mgr.set("dock", "auto_hide", auto_hide)
        self.config_mgr.set("dock", "notch_enabled", notch_enabled)
        self.config_mgr.set("dock", "trigger_mode", trigger)
        self.config_mgr.set("dock", "scale_percent", scale_pct)
        self.config_mgr.set("dock", "element_spacing", spacing)
        self.config_mgr.set("dock", "base_middle_height", base_mid)
        self.config_mgr.set("dock", "element_order", list(self.element_order))

        self.config_mgr.set("colors", "background_r", round(bg_rgba.red, 3))
        self.config_mgr.set("colors", "background_g", round(bg_rgba.green, 3))
        self.config_mgr.set("colors", "background_b", round(bg_rgba.blue, 3))
        self.config_mgr.set("colors", "background_a", round(bg_a, 3))

        self.config_mgr.set("colors", "ram_ring", [round(ram_rgba.red, 3), round(ram_rgba.green, 3), round(ram_rgba.blue, 3)])
        self.config_mgr.set("colors", "cpu_ring", [round(cpu_rgba.red, 3), round(cpu_rgba.green, 3), round(cpu_rgba.blue, 3)])
        self.config_mgr.set("colors", "disk_ring", [round(disk_rgba.red, 3), round(disk_rgba.green, 3), round(disk_rgba.blue, 3)])
        self.config_mgr.set("colors", "notch_color", [round(notch_rgba.red, 3), round(notch_rgba.green, 3), round(notch_rgba.blue, 3)])

        self.config_mgr.set("safety", "sound_alert_enabled", sound)
        self.config_mgr.set("safety", "sound_threshold_percent", sound_thresh)
        self.config_mgr.set("safety", "kill_threshold_percent", kill_thresh)
        self.config_mgr.set("ui", "show_manual_kill_buttons", manual_kill)
        self.config_mgr.set("ui", "use_friendly_names", friendly_names)
        self.config_mgr.set("ui", "refresh_interval_ms", refresh_ms)

        self.config_mgr.save()

        if self.on_changed:
            self.on_changed()
