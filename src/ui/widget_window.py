"""
ZeroFreeze - Janela Principal do Widget Lateral (Dock Auto-Hide)

Melhorias desta versão:
- Forma "quebra-molas" fiel à referência visual: borda colada na tela reta,
  extremidades com curvas orgânicas suaves e generosas (bezier cúbico proporcional).
- Animação de mola (spring physics) com velocidade e amortecimento para
  movimento muito mais suave e natural.
- Layout multi-borda corrigido: ao mudar de borda, restrói o box de gauges
  corretamente, evitando ícones sumindo ou dock com forma errada.
- Cada disco abre popup exclusivo identificado pelo mountpoint.
"""

import math
import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GObject

from src.ui.radial_gauge import RadialGauge
from src.ui.popups import PopupManager

# Constantes analíticas consolidadas da silhueta aprovada pelo Linker (calibração base 74%)
SILHOUETTE_BLUE_DIAM = 87
SILHOUETTE_RED_DIAM = 109
SILHOUETTE_POS_BLUE = 18
SILHOUETTE_POS_RED = 111
SILHOUETTE_TAIL_SIZE = 53


class WidgetWindow(Gtk.Window):
    def __init__(self, config_manager, monitor, anti_freeze_guard):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.config_mgr = config_manager
        self.monitor = monitor
        self.anti_freeze = anti_freeze_guard

        # Configurações da janela — popup sem decorações e sem roubar foco
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.set_app_paintable(True)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        # --- Lê configurações de posicionamento ---
        self.edge = self.config_mgr.get("dock", "edge", "right")
        if self.edge not in ["right", "left"]:
            self.edge = "right"
        self.offset_pct = self.config_mgr.get("dock", "offset_percent", 50)
        self.auto_hide = self.config_mgr.get("dock", "auto_hide", True)
        self.trigger_mode = self.config_mgr.get("dock", "trigger_mode", "hover")
        self.peek_size = self.config_mgr.get("dock", "peek_size_px", 8)

        # Inicia a thread sentinela anti-freeze independente
        if hasattr(self.anti_freeze, "start_sentinel"):
            self.anti_freeze.start_sentinel()

        # --- Estado da animação de mola ---
        # anim_progress: 0.0 = recolhido, 1.0 = expandido
        self.anim_progress = 0.0 if self.auto_hide else 1.0
        self.anim_target = self.anim_progress
        self.anim_velocity = 0.0        # Velocidade atual da animação de mola
        self.anim_timer_id = None
        self.hide_delay_timer_id = None
        self.refresh_timer_id = None
        self.is_pointer_inside = False

        self.current_metrics = {}

        # --- Box dos medidores ---
        self.box_gauges = Gtk.Box(
            orientation=self._get_box_orientation(),
            spacing=10
        )
        self._update_box_margins()
        self.add(self.box_gauges)

        # --- Cores configuradas ---
        ram_c = self.config_mgr.get("colors", "ram_ring", [1.0, 0.45, 0.0])
        cpu_c = self.config_mgr.get("colors", "cpu_ring", [0.15, 0.85, 0.55])

        self.hover_popup_timer_id = None

        # --- Medidores fixos: RAM e CPU ---
        gauge_sz = self._get_gauge_size()
        self.gauge_ram = RadialGauge("RAM", "⚡", default_color=tuple(ram_c), size=gauge_sz)
        self.gauge_ram.connect("gauge-clicked", lambda g: self._on_gauge_clicked("ram"))
        self.gauge_ram.connect("gauge-hovered", lambda g: self._on_gauge_hovered("ram"))

        self.gauge_cpu = RadialGauge("CPU", "✹", default_color=tuple(cpu_c), size=gauge_sz)
        self.gauge_cpu.connect("gauge-clicked", lambda g: self._on_gauge_clicked("cpu"))
        self.gauge_cpu.connect("gauge-hovered", lambda g: self._on_gauge_hovered("cpu"))

        # Lista de (RadialGauge, disk_info_inicial)
        self.disk_gauges = []

        # Popula o box de gauges pela primeira vez
        self._rebuild_gauge_box()

        # --- Gerenciador de pop-ups ---
        self.popup_mgr = PopupManager(self, on_kill_app_callback=self._kill_app_requested)

        # --- Eventos ---
        self.add_events(
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK
        )
        self.connect("draw", self.on_draw)
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)
        self.connect("button-press-event", self.on_mouse_click)
        self.connect("size-allocate", self._on_size_allocate)

        # Monitora adição/remoção de monitores (multi-monitor)
        display = Gdk.Display.get_default()
        if display:
            display.connect("monitor-added", lambda d, m: self._on_monitors_changed())
            display.connect("monitor-removed", lambda d, m: self._on_monitors_changed())

        # --- Primeira leitura de métricas ---
        self._on_tick_update()
        self._start_refresh_timer()

        # Posicionamento inicial (após GTK processar o layout)
        GLib.idle_add(self._apply_layout_and_position)

    # =========================================================================
    # UTILITÁRIOS DE LAYOUT E ESCALA
    # =========================================================================

    def _get_gauge_size(self):
        """Retorna o diâmetro dos medidores baseado na escala configurada (33% a 100%)."""
        scale_pct = self.config_mgr.get("dock", "scale_percent", 100)
        scale = max(0.33, min(1.0, scale_pct / 100.0))
        return max(18, int(54 * scale))

    def _get_transition_params(self):
        """Retorna os parâmetros geométricos consolidados da silhueta, escalados proporcionalmente."""
        scale_pct = self.config_mgr.get("dock", "scale_percent", 74)
        scale = max(0.33, min(1.0, scale_pct / 100.0))

        # Valores exatos calibrados pelo Linker nas barras de ajuste fino:
        diam_blue = SILHOUETTE_BLUE_DIAM * scale
        diam_red = SILHOUETTE_RED_DIAM * scale
        pos_blue = SILHOUETTE_POS_BLUE * scale
        pos_red = SILHOUETTE_POS_RED * scale
        tail_size = SILHOUETTE_TAIL_SIZE * scale

        R_blue = max(4.0 * scale, diam_blue / 2.0)
        R_red = max(8.0 * scale, diam_red / 2.0)

        # Distância vertical entre os dois centros para definir a caída:
        W = 72.0 * scale
        vx = (R_blue + R_red) - W
        min_dy = math.sqrt(max(0.0, (R_blue + R_red)**2 - vx**2))
        dy = max(min_dy, pos_red - pos_blue)

        # A transição total (altura da Fatia 1 e da Fatia 3)
        trans = tail_size + dy + pos_blue

        return scale, diam_blue, diam_red, pos_blue, pos_red, tail_size, trans

    def _get_box_orientation(self):
        """Retorna orientação do box conforme a borda atual."""
        return Gtk.Orientation.VERTICAL if self.edge in ["left", "right"] else Gtk.Orientation.HORIZONTAL

    def _update_box_margins(self):
        """Ajusta margens do box sincronizadas com a base e a distância entre elementos."""
        scale, _, _, _, _, _, trans = self._get_transition_params()

        elem_spacing = int(self.config_mgr.get("dock", "element_spacing", 12))
        fatia2_h = float(self.config_mgr.get("dock", "base_middle_height", 140)) * scale

        self.box_gauges.set_spacing(elem_spacing)

        num_gauges = len(self.box_gauges.get_children())
        if num_gauges == 0:
            num_gauges = 4

        gauge_sz = self._get_gauge_size()
        gauge_h = gauge_sz + max(14, int(22 * (gauge_sz / 54.0)))
        gauge_w = gauge_sz + max(4, int(8 * (gauge_sz / 54.0)))

        h_elems = num_gauges * gauge_h + max(0, num_gauges - 1) * elem_spacing
        H_base = 2.0 * trans + fatia2_h
        H_win = max(H_base, h_elems + 24)

        m_top = max(0, int((H_win - h_elems) / 2.0))
        m_side = max(8, int(15 * scale))

        if self.edge in ["left", "right"]:
            self.box_gauges.set_margin_top(m_top)
            self.box_gauges.set_margin_bottom(m_top)
            self.box_gauges.set_margin_start(m_side)
            self.box_gauges.set_margin_end(m_side)
            W_win = gauge_w + 2 * m_side
            self.set_size_request(int(W_win), int(H_win))
        else:  # top / bottom
            self.box_gauges.set_margin_top(m_side)
            self.box_gauges.set_margin_bottom(m_side)
            self.box_gauges.set_margin_start(m_top)
            self.box_gauges.set_margin_end(m_top)
            W_win = gauge_w + 2 * m_side
            self.set_size_request(int(H_win), int(W_win))

    def _rebuild_gauge_box(self):
        """
        Organiza os gauges rigorosamente na ordem configurada pelo usuário:
        'ram', 'cpu', 'storage' (ou qualquer ordenação personalizada).
        """
        for child in list(self.box_gauges.get_children()):
            self.box_gauges.remove(child)

        if not self.disk_gauges:
            self._create_disk_gauges()

        order = self.config_mgr.get("dock", "element_order", ["ram", "cpu", "storage"])
        groups = {
            "ram": [self.gauge_ram],
            "cpu": [self.gauge_cpu],
            "storage": [dg for dg, _ in self.disk_gauges]
        }

        for key in order:
            for g in groups.get(key, []):
                self.box_gauges.pack_start(g, False, False, 0)

    def _create_disk_gauges(self):
        """Cria os RadialGauges para cada disco detectado com tamanho escalável e hover."""
        self.disk_gauges = []
        storage = self.monitor.get_storage_metrics()
        disk_c = self.config_mgr.get("colors", "disk_ring", [0.95, 0.80, 0.15])
        gauge_sz = self._get_gauge_size()

        for disk in storage.get("disks", []):
            mountpoint = disk["mountpoint"]
            dg = RadialGauge(disk["label"], "💾", default_color=tuple(disk_c), size=gauge_sz)
            dg.mountpoint = mountpoint
            dg.connect(
                "gauge-clicked",
                lambda g, mp=mountpoint: self._on_gauge_clicked(f"disk_mp_{mp}")
            )
            dg.connect(
                "gauge-hovered",
                lambda g, mp=mountpoint: self._on_gauge_hovered(f"disk_mp_{mp}")
            )
            self.disk_gauges.append((dg, disk))

    # =========================================================================
    # TIMER E ATUALIZAÇÃO DE MÉTRICAS
    # =========================================================================

    def _start_refresh_timer(self):
        """Inicia ou reinicia o timer de atualização periódica."""
        if self.refresh_timer_id:
            GLib.source_remove(self.refresh_timer_id)
            self.refresh_timer_id = None
        refresh_ms = self.config_mgr.get("ui", "refresh_interval_ms", 2000)
        self.refresh_timer_id = GLib.timeout_add(refresh_ms, self._on_tick_update)

    def _on_tick_update(self):
        """Coleta métricas em tempo real e atualiza os anéis visuais."""
        try:
            ram = self.monitor.get_ram_metrics()
            cpu = self.monitor.get_cpu_metrics()
            storage = self.monitor.get_storage_metrics()

            self.current_metrics = {
                "ram": ram,
                "cpu": cpu,
                "storage": storage,
                "top_ram_apps": self.monitor.get_top_memory_apps(limit=5),
                "top_cpu_apps": self.monitor.get_top_cpu_apps(limit=5)
            }

            self.gauge_ram.set_percent(ram["percent"])
            self.gauge_cpu.set_percent(cpu["percent"])

            # Atualiza cada gauge de disco pelo mountpoint
            disks_map = {d["mountpoint"]: d for d in storage.get("disks", [])}
            for dg, disk_info in self.disk_gauges:
                mp = disk_info["mountpoint"]
                if mp in disks_map:
                    dg.set_percent(disks_map[mp]["percent"])

            # Verificação de salvaguarda anti-freeze
            self.anti_freeze.check_and_safeguard(ram)

        except Exception as e:
            print(f"[ZeroFreeze] Erro na atualização de métricas: {e}")

        return True  # Continua o timer

    # =========================================================================
    # CLIQUES E POPUPS
    # =========================================================================

    def _on_gauge_clicked(self, gauge_type):
        """Abre a janela flutuante independente para o gauge clicado."""
        manual_kill = self.config_mgr.get("ui", "show_manual_kill_buttons", False)
        self.popup_mgr.show_popup(gauge_type, self.current_metrics, manual_kill_enabled=manual_kill)

    def _on_gauge_hovered(self, gauge_type):
        """Abre o popup ao passar o mouse por cima do gauge de forma rápida e confiável."""
        if self.hover_popup_timer_id:
            GLib.source_remove(self.hover_popup_timer_id)
            self.hover_popup_timer_id = None

        # Se já existe um popup aberto, a troca entre os medidores é INSTANTÂNEA
        if self.popup_mgr.is_visible():
            self._on_gauge_clicked(gauge_type)
            return

        # Debounce ultrarrápido de 30ms apenas para filtrar passagem relâmpago do mouse
        self.hover_popup_timer_id = GLib.timeout_add(30, self._open_hover_popup, gauge_type)

    def _open_hover_popup(self, gauge_type):
        self.hover_popup_timer_id = None
        self._on_gauge_clicked(gauge_type)
        return False

    def _kill_app_requested(self, root_pid):
        self.anti_freeze.kill_application_tree(root_pid)
        self._on_tick_update()

    # =========================================================================
    # AUTO-HIDE E EVENTOS DE MOUSE
    # =========================================================================

    def on_mouse_enter(self, widget, event):
        self.is_pointer_inside = True
        if self.auto_hide and self.trigger_mode == "hover":
            if self.hide_delay_timer_id:
                GLib.source_remove(self.hide_delay_timer_id)
                self.hide_delay_timer_id = None
            self._animate_to(1.0)
        return False

    def on_mouse_leave(self, widget, event):
        self.is_pointer_inside = False
        if self.auto_hide and self.trigger_mode == "hover":
            if self.hide_delay_timer_id:
                GLib.source_remove(self.hide_delay_timer_id)
            self.hide_delay_timer_id = GLib.timeout_add(800, self._trigger_hide_after_delay)
        return False

    def on_popup_dismissed(self):
        """Chamado quando um popup de detalhe é fechado (ex: perda de foco ao clicar fora)."""
        if self.auto_hide and not self.is_pointer_inside:
            self._animate_to(0.0)

    def _trigger_hide_after_delay(self):
        """Recolhe a dock se nenhum popup estiver aberto."""
        if self.popup_mgr.is_visible():
            self.hide_delay_timer_id = None
            return False
        self._animate_to(0.0)
        self.hide_delay_timer_id = None
        return False

    def on_mouse_click(self, widget, event):
        if event.button == 3:  # Botão direito → menu de contexto
            self._show_context_menu(event)
            return True
        elif event.button == 1 and self.auto_hide and self.trigger_mode == "click":
            target = 0.0 if self.anim_progress > 0.5 else 1.0
            self._animate_to(target)
            return True
        return False

    # =========================================================================
    # ANIMAÇÃO DE MOLA (SPRING PHYSICS)
    # =========================================================================

    def _animate_to(self, target):
        """Define o alvo da animação e inicia o loop se necessário."""
        self.anim_target = target
        if not self.anim_timer_id:
            self.anim_timer_id = GLib.timeout_add(16, self._on_anim_step)

    def _on_anim_step(self):
        """
        Animação de mola (spring physics) a ~60 FPS.
        
        A velocidade acelera em direção ao alvo (proporcional à distância)
        e é amortecida a cada frame. O resultado é um movimento que
        começa rápido e desacelera suavemente antes de parar — muito mais
        orgânico do que uma simples interpolação linear.
        
        Parâmetros ajustados para sensação de mola firme e fluida:
        - spring_k=0.09: quanto o erro "puxa" a velocidade (maior = mais rígido)
        - damping=0.72:  quanto a velocidade decai a cada frame (menor = mais elástico)
        """
        delta = self.anim_target - self.anim_progress

        # Verifica convergência
        if abs(delta) < 0.004 and abs(self.anim_velocity) < 0.003:
            self.anim_progress = self.anim_target
            self.anim_velocity = 0.0
            self._update_window_position()
            self.anim_timer_id = None
            return False  # Para o timer

        # Física de mola: F = k * x, amortecimento viscoso
        spring_k = 0.09
        damping = 0.72
        self.anim_velocity = self.anim_velocity * damping + delta * spring_k
        self.anim_progress = max(0.0, min(1.0, self.anim_progress + self.anim_velocity))

        self._update_window_position()
        return True

    # =========================================================================
    # MENU DE CONTEXTO E CONFIGURAÇÕES
    # =========================================================================

    def _show_context_menu(self, event):
        menu = Gtk.Menu()

        item_config = Gtk.MenuItem(label="⚙️  Configurações do ZeroFreeze")
        item_config.connect("activate", self._open_settings_dialog)
        menu.append(item_config)

        menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem(label="✕  Sair do ZeroFreeze")
        item_quit.connect("activate", lambda i: Gtk.main_quit())
        menu.append(item_quit)

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)

    def _open_settings_dialog(self, widget):
        from src.ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(
            self, self.config_mgr,
            on_settings_changed_callback=self._on_settings_applied
        )
        try:
            dlg.run()
        finally:
            dlg.destroy()

    def _on_settings_applied(self):
        """
        Aplica imediatamente todas as mudanças de configuração:
        borda, orientação, cores, monitor alvo e taxa de atualização.
        """
        new_edge = self.config_mgr.get("dock", "edge", "right")
        old_is_vertical = self.edge in ["left", "right"]
        new_is_vertical = new_edge in ["left", "right"]

        self.edge = new_edge
        self.offset_pct = self.config_mgr.get("dock", "offset_percent", 50)
        self.auto_hide = self.config_mgr.get("dock", "auto_hide", True)
        self.trigger_mode = self.config_mgr.get("dock", "trigger_mode", "hover")

        # Atualiza orientação do box de medidores
        self.box_gauges.set_orientation(self._get_box_orientation())
        self._update_box_margins()

        # Reconstrói o box para garantir orientação e ordem dos elementos atualizadas
        self._rebuild_gauge_box()

        # Atualiza tamanho dos gauges baseado na escala (33% a 100%)
        gauge_sz = self._get_gauge_size()
        self.gauge_ram.set_size(gauge_sz)
        self.gauge_cpu.set_size(gauge_sz)
        for dg, _ in self.disk_gauges:
            dg.set_size(gauge_sz)

        # Atualiza cores dos anéis
        ram_c = self.config_mgr.get("colors", "ram_ring", [1.0, 0.45, 0.0])
        cpu_c = self.config_mgr.get("colors", "cpu_ring", [0.15, 0.85, 0.55])
        disk_c = self.config_mgr.get("colors", "disk_ring", [0.95, 0.80, 0.15])

        self.gauge_ram.default_color = tuple(ram_c)
        self.gauge_ram.area.queue_draw()
        self.gauge_cpu.default_color = tuple(cpu_c)
        self.gauge_cpu.area.queue_draw()
        for dg, _ in self.disk_gauges:
            dg.default_color = tuple(disk_c)
            dg.area.queue_draw()

        # Reinicia timer de atualização (pode ter mudado a frequência)
        self._start_refresh_timer()

        # Reseta posição da animação para o novo estado
        self.anim_progress = 0.0 if self.auto_hide else 1.0
        self.anim_target = self.anim_progress
        self.anim_velocity = 0.0

        # Fecha qualquer popup aberto
        self.popup_mgr.close_popup()

        # Força o recálculo do layout da janela inteira
        self.box_gauges.queue_resize()
        self.queue_resize()
        self.show_all()
        GLib.idle_add(self._apply_layout_and_position)
        self.queue_draw()

    # =========================================================================
    # MULTI-MONITOR E POSICIONAMENTO
    # =========================================================================

    def _on_monitors_changed(self):
        print("[ZeroFreeze] Alteração de monitores detectada! Reposicionando...")
        GLib.idle_add(self._apply_layout_and_position)

    def _get_target_monitor_geometry(self):
        """Retorna a geometria do monitor alvo, com fallback automático para o principal."""
        display = Gdk.Display.get_default()
        n_mons = display.get_n_monitors()
        target_mon = str(self.config_mgr.get("dock", "target_monitor", "primary"))

        monitor = None
        if target_mon != "primary" and target_mon.isdigit():
            idx = int(target_mon)
            if idx < n_mons:
                m = display.get_monitor(idx)
                if m and (not hasattr(m, "is_valid") or m.is_valid()):
                    monitor = m

        if not monitor:
            monitor = display.get_primary_monitor() or display.get_monitor(0)

        return monitor.get_geometry()

    def _apply_layout_and_position(self):
        """Força o GTK a recalcular o layout natural e reposiciona a dock."""
        self.show_all()
        self.resize(1, 1)  # Compacta para o tamanho natural do conteúdo
        self.queue_resize()
        GLib.idle_add(self._update_window_position)
        GLib.idle_add(self._update_input_shape)
        return False

    def _on_size_allocate(self, widget, allocation):
        """Chamado pelo GTK quando as dimensões da janela são alocadas."""
        self._update_window_position()
        self._update_input_shape()

    def _update_window_position(self):
        """Calcula e aplica as coordenadas x, y da dock considerando anim_progress e alcance vertical completo."""
        geo = self._get_target_monitor_geometry()

        # Obtém tamanho real alocado pelo GTK
        alloc = self.get_allocation()
        w = alloc.width if alloc.width > 1 else self.get_size()[0]
        h = alloc.height if alloc.height > 1 else self.get_size()[1]
        w = max(w, 24)
        h = max(h, 24)

        offset = self.offset_pct / 100.0
        t = self.anim_progress  # 0.0 = recolhido, 1.0 = expandido

        scale, _, _, _, _, _, trans = self._get_transition_params()
        fatia2_h = float(self.config_mgr.get("dock", "base_middle_height", 140)) * scale
        H_base = 2.0 * trans + fatia2_h

        if self.edge in ["right", "left"]:
            y_base_top = max(0.0, (h - H_base) / 2.0)
            y_start = geo.y - y_base_top
            y_end = geo.y + geo.height - y_base_top - H_base
            cur_y = int(y_start + (y_end - y_start) * offset)

            if self.edge == "right":
                x_ret = geo.x + geo.width - self.peek_size
                x_exp = geo.x + geo.width - w
                cur_x = int(x_ret + (x_exp - x_ret) * t)
            else:  # left
                x_ret = geo.x - (w - self.peek_size)
                x_exp = geo.x
                cur_x = int(x_ret + (x_exp - x_ret) * t)

        else:  # top / bottom
            x_base_left = max(0.0, (w - H_base) / 2.0)
            x_start = geo.x - x_base_left
            x_end = geo.x + geo.width - x_base_left - H_base
            cur_x = int(x_start + (x_end - x_start) * offset)

            if self.edge == "top":
                y_ret = geo.y - (h - self.peek_size)
                y_exp = geo.y
                cur_y = int(y_ret + (y_exp - y_ret) * t)
            else:  # bottom
                y_ret = geo.y + geo.height - self.peek_size
                y_exp = geo.y + geo.height - h
                cur_y = int(y_ret + (y_exp - y_ret) * t)

        self.window_cur_x = cur_x
        self.window_cur_y = cur_y
        self.move(cur_x, cur_y)
        self._update_input_shape()
        self.queue_draw()
        return False

    def _trace_dock_path(self, cr, width, height):
        """Constrói o contorno fechado da base da dock em coordenadas Cairo."""
        scale, diam_blue, diam_red, pos_blue, pos_red, tail_size, trans = self._get_transition_params()

        is_vertical = self.edge in ["left", "right"]
        W = float(width if is_vertical else height)
        H = float(height if is_vertical else width)

        fatia2_h = float(self.config_mgr.get("dock", "base_middle_height", 140)) * scale
        H_base = 2.0 * trans + fatia2_h
        y_base_top = max(0.0, (H - H_base) / 2.0)

        R_blue = max(4.0 * scale, diam_blue / 2.0)
        R_red = max(8.0 * scale, diam_red / 2.0)
        y_red = tail_size

        x_red = W - R_red
        x_blue = R_blue

        R_sum = R_blue + R_red
        vx = x_blue - x_red
        min_dy = math.sqrt(max(0.0, R_sum**2 - vx**2))

        dy = max(min_dy, pos_red - pos_blue)
        y_blue = y_red + dy

        D = math.hypot(vx, dy)

        if D >= R_sum:
            angle_V = math.atan2(dy, vx)
            gamma = math.acos(min(1.0, R_sum / D))
            theta = angle_V - gamma

            t1_x = x_red + R_red * math.cos(theta)
            t1_y = y_red + R_red * math.sin(theta)

            t2_x = x_blue - R_blue * math.cos(theta)
            t2_y = y_blue - R_blue * math.sin(theta)

            ang1_c2 = math.atan2(t2_y - y_blue, t2_x - x_blue)
            ang2_c2 = -math.pi

            cr.save()

            if self.edge == "right":
                cr.translate(0.0, y_base_top)
            elif self.edge == "left":
                cr.translate(W, y_base_top)
                cr.scale(-1.0, 1.0)
            elif self.edge == "top":
                cr.translate(y_base_top, W)
                cr.rotate(-math.pi / 2.0)
            elif self.edge == "bottom":
                cr.translate(H - y_base_top, 0.0)
                cr.rotate(math.pi / 2.0)

            # Traçado da base (Fatias 1, 2 e 3 com altura H_base):
            cr.move_to(W, 0.0)
            cr.line_to(W, y_red)
            cr.arc(x_red, y_red, R_red, 0.0, theta)
            cr.line_to(t2_x, t2_y)
            cr.arc_negative(x_blue, y_blue, R_blue, ang1_c2, ang2_c2)
            cr.line_to(0.0, H_base - trans)

            # Simetria inferior (Fatia 3)
            cr.arc_negative(x_blue, H_base - y_blue, R_blue, ang2_c2, -ang1_c2)
            cr.line_to(t1_x, H_base - t1_y)
            cr.arc(x_red, H_base - y_red, R_red, -theta, 0.0)
            cr.line_to(W, H_base)
            cr.line_to(W, 0.0)
            cr.close_path()

            cr.restore()

    def _update_input_shape(self):
        """
        Gera uma máscara de forma (input shape e window shape) para a janela GDK baseada
        estritamente no desenho da silhueta Cairo, e CORTA milimetricamente qualquer
        região que ultrapasse as fronteiras do monitor alvo (eliminando 100% o vazamento
        entre múltiplos monitores quando em auto-hide).
        """
        win = self.get_window()
        if not win:
            return

        alloc = self.get_allocation()
        width = alloc.width
        height = alloc.height
        if width <= 1 or height <= 1:
            return

        geo = self._get_target_monitor_geometry()
        cur_x = getattr(self, "window_cur_x", geo.x)

        # Limites locais correspondentes ao monitor alvo
        clip_x1 = max(0, geo.x - cur_x)
        clip_x2 = min(width, geo.x + geo.width - cur_x)
        clip_w = max(0, clip_x2 - clip_x1)

        surface = cairo.ImageSurface(cairo.FORMAT_A1, width, height)
        cr = cairo.Context(surface)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)

        # Corta qualquer pixel que saia do monitor configurado
        if clip_w > 0:
            cr.rectangle(clip_x1, 0, clip_w, height)
            cr.clip()

        # Pinta estritamente e exclusivamente a silhueta da base da dock
        self._trace_dock_path(cr, width, height)
        cr.fill()

        region = Gdk.cairo_region_create_from_surface(surface)
        win.shape_combine_region(region, 0, 0)
        win.input_shape_combine_region(region, 0, 0)

    # =========================================================================
    # DESENHO CAIRO — SILHUETA PARAMETRIZADA POR CONTROLES FINOS
    # =========================================================================

    def on_draw(self, widget, cr):
        """
        Desenha a silhueta da dock utilizando as cores e formato consolidados.
        Aplica corte estrito nos limites do monitor alvo para impedir vazamento visual.
        """
        width = self.get_allocated_width()
        height = self.get_allocated_height()

        # Contenção multi-monitor: não desenha fora do monitor alvo
        geo = self._get_target_monitor_geometry()
        cur_x = getattr(self, "window_cur_x", geo.x)
        clip_x1 = max(0, geo.x - cur_x)
        clip_x2 = min(width, geo.x + geo.width - cur_x)
        clip_w = max(0, clip_x2 - clip_x1)
        if clip_w > 0:
            cr.rectangle(clip_x1, 0, clip_w, height)
            cr.clip()

        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # Cores de fundo da configuração
        bg_r = self.config_mgr.get("colors", "background_r", 0.06)
        bg_g = self.config_mgr.get("colors", "background_g", 0.07)
        bg_b = self.config_mgr.get("colors", "background_b", 0.09)
        bg_a = self.config_mgr.get("colors", "background_a", 0.94)
        cr.set_source_rgba(bg_r, bg_g, bg_b, bg_a)

        self._trace_dock_path(cr, width, height)
        cr.fill_preserve()

        # Borda translúcida sutil para profundidade
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.10)
        cr.set_line_width(1.2)
        cr.stroke()

        # Barrinha luminosa (entalhe) quando recolhida
        self._draw_notch(cr, width, height)

        return False

    def _draw_notch(self, cr, width, height):
        """
        Desenha a barrinha luminosa (entalhe) na ponta externa da base recolhida
        para orientar o usuário na localização da dock quando o Auto-Hide está ativo.
        """
        if not self.config_mgr.get("dock", "auto_hide", True):
            return
        if not self.config_mgr.get("dock", "notch_enabled", True):
            return

        # Opacidade: 1.0 quando recolhida, esmaecendo até 0.0 quando expandida
        alpha = max(0.0, 1.0 - self.anim_progress)
        if alpha <= 0.01:
            return

        scale, _, _, _, _, _, trans = self._get_transition_params()
        fatia2_h = float(self.config_mgr.get("dock", "base_middle_height", 140)) * scale
        H_base = 2.0 * trans + fatia2_h

        is_vertical = self.edge in ["left", "right"]
        W = float(width if is_vertical else height)
        H = float(height if is_vertical else width)
        y_base_top = max(0.0, (H - H_base) / 2.0)

        # Dimensões da pílula do entalhe
        notch_len = max(24.0 * scale, min(fatia2_h * 0.55, 80.0 * scale))
        notch_thick = max(3.5, 4.5 * scale)
        corner_r = notch_thick / 2.0

        notch_c = self.config_mgr.get("colors", "notch_color", [0.0, 0.28, 1.0])
        nr, ng, nb = notch_c[0], notch_c[1], notch_c[2]

        cr.save()

        if self.edge == "right":
            cr.translate(0.0, y_base_top)
        elif self.edge == "left":
            cr.translate(W, y_base_top)
            cr.scale(-1.0, 1.0)
        elif self.edge == "top":
            cr.translate(y_base_top, W)
            cr.rotate(-math.pi / 2.0)
        elif self.edge == "bottom":
            cr.translate(H - y_base_top, 0.0)
            cr.rotate(math.pi / 2.0)

        y_center = H_base / 2.0
        ny = y_center - notch_len / 2.0
        nx = 1.0

        # Pílula arredondada
        cr.new_sub_path()
        cr.arc(nx + corner_r, ny + corner_r, corner_r, math.pi, 1.5 * math.pi)
        cr.arc(nx + notch_thick - corner_r, ny + corner_r, corner_r, 1.5 * math.pi, 2.0 * math.pi)
        cr.arc(nx + notch_thick - corner_r, ny + notch_len - corner_r, corner_r, 0.0, 0.5 * math.pi)
        cr.arc(nx + corner_r, ny + notch_len - corner_r, corner_r, 0.5 * math.pi, math.pi)
        cr.close_path()

        # Preenchimento com cor configurada e opacidade
        cr.set_source_rgba(nr, ng, nb, alpha * 0.95)
        cr.fill_preserve()

        # Brilho / reflexo sutil
        cr.set_source_rgba(1.0, 1.0, 1.0, alpha * 0.35)
        cr.set_line_width(0.8)
        cr.stroke()

        cr.restore()
