"""
ZeroFreeze - Janelas Flutuantes de Detalhes (Pop-ups / Flyout Windows)

Cada janela é INDEPENDENTE e DESCARTÁVEL:
- Sempre que um novo gauge é clicado, a janela anterior é destruída.
- Uma nova janela é criada do zero para o gauge clicado.
- Cada disco tem seu próprio pop-up exclusivo com suas estatísticas.
- O posicionamento é calculado APÓS o GTK alocar o tamanho real (via idle_add).
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango
from src.ui.icons import draw_ram_icon, draw_cpu_icon, draw_disk_icon

CSS_POPUP = b"""
window.flyout-window {
    background-color: transparent;
}
.flyout-card {
    background-color: rgba(12, 14, 18, 0.97);
    border: 1px solid rgba(255, 255, 255, 0.13);
    border-radius: 14px;
    padding: 14px 16px;
    color: #e4e7eb;
}
.flyout-title {
    font-weight: 700;
    font-size: 14px;
    color: #ffffff;
    margin-bottom: 2px;
}
.flyout-subtitle {
    font-size: 11px;
    color: #9aa0a6;
}
.section-label {
    font-size: 11px;
    font-weight: 600;
    color: #76a0d0;
    margin-top: 4px;
}
.app-row {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    padding: 6px 10px;
    margin-bottom: 4px;
}
.app-row:hover {
    background-color: rgba(255, 255, 255, 0.09);
    border-color: rgba(255, 255, 255, 0.14);
}
.app-name {
    font-weight: 600;
    font-size: 12px;
    color: #ffffff;
}
.app-badge {
    font-size: 10px;
    color: #76a0d0;
    background-color: rgba(66, 133, 244, 0.16);
    border-radius: 4px;
    padding: 1px 5px;
}
.app-size {
    font-size: 12px;
    font-weight: bold;
    color: #2ed573;
}
.app-size-zero {
    font-size: 12px;
    font-weight: bold;
    color: #ffffff;
}
.cpu-pct {
    font-size: 12px;
    font-weight: bold;
    color: #2ed573;
}
.cpu-pct-zero {
    font-size: 12px;
    font-weight: bold;
    color: #ffffff;
}
.btn-kill {
    background-color: rgba(234, 67, 53, 0.16);
    border: 1px solid rgba(234, 67, 53, 0.4);
    color: #ff6b6b;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
}
.btn-kill:hover {
    background-color: rgba(234, 67, 53, 0.4);
    color: #ffffff;
}
.btn-close {
    color: #6e7680;
    font-size: 14px;
    padding: 0 2px;
    min-width: 0;
}
.btn-close:hover {
    color: #ffffff;
}
.stat-box {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 8px;
    padding: 8px 12px;
}
.stat-label {
    font-size: 10px;
    color: #7a8390;
    letter-spacing: 0.5px;
}
.stat-val {
    font-size: 13px;
    font-weight: 600;
    color: #ffffff;
}
.stat-val-green {
    font-size: 13px;
    font-weight: 600;
    color: #2ed573;
}
.stat-val-blue {
    font-size: 13px;
    font-weight: 600;
    color: #2ed573;
}
.stat-val-warn {
    font-size: 13px;
    font-weight: 600;
    color: #2ed573;
}
progress, trough {
    border-radius: 4px;
    min-height: 5px;
}
trough {
    background-color: rgba(255, 255, 255, 0.10);
}
progress {
    background-color: #2ed573;
}
"""



class BasePopupWindow(Gtk.Window):
    """Janela base para pop-ups descartáveis e independentes."""

    def __init__(self, parent_window):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.parent_window = parent_window

        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_app_paintable(True)
        self.set_resizable(False)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS_POPUP)
        Gtk.StyleContext.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.get_style_context().add_class("flyout-window")
        self.connect("draw", self._on_draw)

        self.set_can_focus(True)
        self.add_events(
            Gdk.EventMask.FOCUS_CHANGE_MASK
        )
        self.connect("focus-out-event", self._on_focus_out)

        # Container principal com borda arredondada
        self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.card.get_style_context().add_class("flyout-card")
        self.add(self.card)

    def _on_focus_out(self, widget, event):
        """Fecha automaticamente o popup e esconde a dock quando o usuário clica fora."""
        if hasattr(self.parent_window, "on_popup_dismissed"):
            self.parent_window.on_popup_dismissed()
        self.destroy()
        return False

    def _on_draw(self, widget, cr):
        cr.set_operator(0)  # CLEAR
        cr.paint()
        cr.set_operator(2)  # OVER
        return False

    def _create_icon_widget(self, icon_type):
        """Cria um widget vetorial Cairo com o mesmo ícone do medidor da dock, em branco puro."""
        da = Gtk.DrawingArea()
        da.set_size_request(20, 20)

        def on_draw(widget, cr):
            alloc = widget.get_allocation()
            cx = alloc.width / 2.0
            cy = alloc.height / 2.0

            cr.set_operator(0)  # CLEAR
            cr.paint()
            cr.set_operator(2)  # OVER

            # Cor branca pura (1.0, 1.0, 1.0) conforme solicitado pelo Linker
            if icon_type == "ram":
                draw_ram_icon(cr, cx, cy, icon_r=1.0, icon_g=1.0, icon_b=1.0, scale=0.85)
            elif icon_type == "cpu":
                draw_cpu_icon(cr, cx, cy, icon_r=1.0, icon_g=1.0, icon_b=1.0, scale=0.85)
            elif icon_type == "disk":
                draw_disk_icon(cr, cx, cy, icon_r=1.0, icon_g=1.0, icon_b=1.0, scale=0.85)
            return False

        da.connect("draw", on_draw)
        return da

    def _create_header(self, title_text, icon="", icon_type=None):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_valign(Gtk.Align.CENTER)

        if icon_type:
            icon_w = self._create_icon_widget(icon_type)
            icon_w.set_valign(Gtk.Align.CENTER)
            header.pack_start(icon_w, False, False, 0)
        elif icon:
            lbl_icon = Gtk.Label(label=icon)
            lbl_icon.set_valign(Gtk.Align.CENTER)
            header.pack_start(lbl_icon, False, False, 0)

        lbl_title = Gtk.Label(label=title_text)
        lbl_title.get_style_context().add_class("flyout-title")
        lbl_title.set_halign(Gtk.Align.START)
        lbl_title.set_valign(Gtk.Align.CENTER)
        header.pack_start(lbl_title, True, True, 0)

        close_btn = Gtk.Button(label="✕")
        close_btn.get_style_context().add_class("btn-close")
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", lambda b: self.destroy())
        header.pack_end(close_btn, False, False, 0)
        return header

    def _make_progress_bar(self, pct, color_class=None):
        """Cria uma barra de progresso compacta e estilizada."""
        pbar = Gtk.ProgressBar()
        pbar.set_fraction(min(1.0, max(0.0, pct / 100.0)))
        return pbar

    def _make_stat_box(self, label_text, value_text, val_class="stat-val"):
        """Cria um bloco de estatística compacto (label em cima, valor embaixo)."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.get_style_context().add_class("stat-box")

        lbl = Gtk.Label(label=label_text)
        lbl.get_style_context().add_class("stat-label")
        lbl.set_halign(Gtk.Align.START)
        box.pack_start(lbl, False, False, 0)

        val = Gtk.Label(label=value_text)
        val.get_style_context().add_class(val_class)
        val.set_halign(Gtk.Align.START)
        box.pack_start(val, False, False, 0)

        return box


class RAMPopupWindow(BasePopupWindow):
    """Pop-up de Memória RAM com ranking e opção de kill manual."""

    def __init__(self, parent_window, data, on_kill_callback=None, manual_kill_enabled=False):
        super().__init__(parent_window)
        self.set_size_request(330, -1)

        ram = data.get("ram", {})
        top_apps = data.get("top_ram_apps", [])

        pct = ram.get("percent", 0.0)
        used = ram.get("used_gb", 0.0)
        total = ram.get("total_gb", 0.0)
        available = ram.get("available_gb", 0.0)

        # --- Cabeçalho ---
        self.card.pack_start(self._create_header("Memória RAM", icon_type="ram"), False, False, 0)

        # --- Resumo geral ---
        sub = Gtk.Label(label=f"Uso: {pct}%  •  {used} GB usados de {total} GB  •  {available} GB livres")
        sub.get_style_context().add_class("flyout-subtitle")
        sub.set_halign(Gtk.Align.START)
        sub.set_line_wrap(True)
        self.card.pack_start(sub, False, False, 0)

        self.card.pack_start(self._make_progress_bar(pct), False, False, 2)
        self.card.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # --- Ranking de apps ---
        lbl_sec = Gtk.Label(label="Top 5 aplicações mais pesadas em RAM:")
        lbl_sec.get_style_context().add_class("section-label")
        lbl_sec.set_halign(Gtk.Align.START)
        self.card.pack_start(lbl_sec, False, False, 0)

        for app in top_apps:
            row = self._build_app_row(app, show_size=True,
                                      kill_enabled=manual_kill_enabled,
                                      on_kill=on_kill_callback)
            self.card.pack_start(row, False, False, 0)

    def _build_app_row(self, app, show_size=True, kill_enabled=False, on_kill=None):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.get_style_context().add_class("app-row")

        # Tooltip completo ao passar o mouse
        tooltip = (
            f"Nome amigável: {app['name']}\n"
            f"Processo real: {app['raw_name']}\n"
            f"PID raiz: {app['root_pid']}  ({app.get('process_count', 1)} processos)\n"
            f"Consumo: {app['size_str']} — {app['percent']}% da RAM\n"
            f"Comando:\n{app.get('cmdline_str', app['raw_name'])}"
        )
        row.set_tooltip_text(tooltip)

        # Coluna de nome e badge
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        lbl_name = Gtk.Label(label=app["name"])
        lbl_name.get_style_context().add_class("app-name")
        lbl_name.set_halign(Gtk.Align.START)
        lbl_name.set_ellipsize(Pango.EllipsizeMode.END)
        lbl_name.set_max_width_chars(20)
        lbl_name.set_tooltip_text(tooltip)
        col.pack_start(lbl_name, False, False, 0)

        proc_cnt = app.get("process_count", 1)
        badge = Gtk.Label(label=f"{proc_cnt} subprocessos" if proc_cnt > 1 else "1 processo")
        badge.get_style_context().add_class("app-badge")
        badge.set_halign(Gtk.Align.START)
        col.pack_start(badge, False, False, 0)

        row.pack_start(col, True, True, 0)

        if show_size:
            sz_str = app.get("size_str", "0 B")
            # Se zerado (ex: "0 B", "0.0 B", "0 MB"), texto em branco; se houver consumo (> 0), verde!
            is_zero = (app.get("rss_bytes", 1) == 0 or sz_str.strip() in ["0 B", "0.0 B", "0 MB", "0.0 MB", "0 GB"])
            lbl_sz = Gtk.Label(label=sz_str)
            lbl_sz.get_style_context().add_class("app-size-zero" if is_zero else "app-size")
            row.pack_start(lbl_sz, False, False, 4)

        if kill_enabled and on_kill:
            pid = app["root_pid"]
            btn = Gtk.Button(label="Fechar")
            btn.get_style_context().add_class("btn-kill")
            btn.connect("clicked", lambda b, p=pid: self._do_kill(p, on_kill))
            row.pack_start(btn, False, False, 0)

        return row

    def _do_kill(self, pid, callback):
        callback(pid)
        self.destroy()


class CPUPopupWindow(BasePopupWindow):
    """Pop-up do Processador (CPU) com ranking de uso."""

    def __init__(self, parent_window, data):
        super().__init__(parent_window)
        self.set_size_request(320, -1)

        cpu = data.get("cpu", {})
        top_apps = data.get("top_cpu_apps", [])

        pct = cpu.get("percent", 0.0)
        cores = cpu.get("count", 0)

        # --- Cabeçalho ---
        self.card.pack_start(self._create_header("Processador (CPU)", icon_type="cpu"), False, False, 0)

        # --- Resumo ---
        sub = Gtk.Label(label=f"Carga total: {pct}%  •  {cores} Núcleos lógicos")
        sub.get_style_context().add_class("flyout-subtitle")
        sub.set_halign(Gtk.Align.START)
        self.card.pack_start(sub, False, False, 0)

        self.card.pack_start(self._make_progress_bar(pct), False, False, 2)
        self.card.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # --- Ranking ---
        lbl_sec = Gtk.Label(label="Top 5 aplicações mais pesadas em CPU:")
        lbl_sec.get_style_context().add_class("section-label")
        lbl_sec.set_halign(Gtk.Align.START)
        self.card.pack_start(lbl_sec, False, False, 0)

        for app in top_apps:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row.get_style_context().add_class("app-row")

            tooltip = (
                f"Nome amigável: {app['name']}\n"
                f"Processo real: {app['raw_name']}\n"
                f"PID: {app.get('root_pid', 'N/A')}\n"
                f"Uso de CPU: {app['percent']}%\n"
                f"Comando:\n{app.get('cmdline_str', app['name'])}"
            )
            row.set_tooltip_text(tooltip)

            lbl_name = Gtk.Label(label=app["name"])
            lbl_name.get_style_context().add_class("app-name")
            lbl_name.set_halign(Gtk.Align.START)
            lbl_name.set_ellipsize(Pango.EllipsizeMode.END)
            lbl_name.set_max_width_chars(22)
            lbl_name.set_tooltip_text(tooltip)
            row.pack_start(lbl_name, True, True, 0)

            cpu_val = float(app.get("percent", 0.0))
            is_zero = (cpu_val <= 0.0)
            lbl_pct = Gtk.Label(label=f"{app['percent']}%")
            lbl_pct.get_style_context().add_class("cpu-pct-zero" if is_zero else "cpu-pct")
            row.pack_start(lbl_pct, False, False, 4)

            self.card.pack_start(row, False, False, 0)


class SingleDiskPopupWindow(BasePopupWindow):
    """
    Pop-up EXCLUSIVO para um único disco/partição específico.
    Exibe todas as estatísticas detalhadas apenas deste disco.
    Largura padrão confortável fixada em 310px (padrão de Sistema).
    Para caminhos longos (ex: SSD Secundário), quebra no bloco de informação em 2 linhas:
      - Linha 1: Ponto de montagem (com reticências se exceder e tooltip com caminho completo)
      - Linha 2: Tipo de partição e dispositivo (com reticências se exceder e tooltip)
    """

    def __init__(self, parent_window, disk_info):
        super().__init__(parent_window)
        self.set_size_request(310, -1)

        label = disk_info.get("label", "Armazenamento")
        mountpoint = disk_info.get("mountpoint", "/")
        device = disk_info.get("device", "/dev/disk")
        fstype = disk_info.get("fstype", "ext4").upper()
        pct = disk_info.get("percent", 0.0)
        used_gb = disk_info.get("used_gb", 0.0)
        total_gb = disk_info.get("total_gb", 0.0)
        free_gb = disk_info.get("free_gb", 0.0)
        r_mb = disk_info.get("read_mb_s", 0.0)
        w_mb = disk_info.get("write_mb_s", 0.0)
        smart = disk_info.get("smart", {})

        # --- Cabeçalho ---
        self.card.pack_start(self._create_header(label, icon_type="disk"), False, False, 0)

        # --- Ponto de montagem e tipo: Bloco fixo de 2 linhas padronizado para 100% de igualdade ---
        full_info_tooltip = f"Ponto de montagem: {mountpoint}\nSistema de arquivos: {fstype}\nDispositivo: {device}"

        box_mount = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        # Linha 1: Ponto de montagem (com reticências se exceder a largura)
        lbl_line1 = Gtk.Label(label=mountpoint)
        lbl_line1.get_style_context().add_class("flyout-subtitle")
        lbl_line1.set_halign(Gtk.Align.START)
        lbl_line1.set_ellipsize(Pango.EllipsizeMode.END)
        lbl_line1.set_max_width_chars(32)
        lbl_line1.set_tooltip_text(f"Ponto de montagem: {mountpoint}")
        box_mount.pack_start(lbl_line1, False, False, 0)

        # Linha 2: Sistema de arquivos e dispositivo (espaço reservado se não houver)
        line2_text = f"{fstype}  •  {device}" if (fstype or device) else " "
        lbl_line2 = Gtk.Label(label=line2_text)
        lbl_line2.get_style_context().add_class("flyout-subtitle")
        lbl_line2.set_halign(Gtk.Align.START)
        lbl_line2.set_ellipsize(Pango.EllipsizeMode.END)
        lbl_line2.set_max_width_chars(32)
        lbl_line2.set_tooltip_text(f"Sistema: {fstype}  •  Dispositivo: {device}")
        box_mount.pack_start(lbl_line2, False, False, 0)

        self.card.pack_start(box_mount, False, False, 0)

        # --- Barra de uso e capacidade em 2 linhas fixas ---
        self.card.pack_start(self._make_progress_bar(pct), False, False, 2)

        box_cap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        lbl_cap_used = Gtk.Label()
        if used_gb > 0:
            lbl_cap_used.set_markup(f"<span color='#2ed573'><b>{used_gb} GB</b></span> usados ({pct}%)")
        else:
            lbl_cap_used.set_text(f"{used_gb} GB usados ({pct}%)")
        lbl_cap_used.get_style_context().add_class("flyout-subtitle")
        lbl_cap_used.set_halign(Gtk.Align.START)
        lbl_cap_used.set_line_wrap(False)
        box_cap.pack_start(lbl_cap_used, False, False, 0)

        lbl_cap_total = Gtk.Label(label=f"Total: {total_gb} GB  •  {free_gb} GB livres")
        lbl_cap_total.get_style_context().add_class("flyout-subtitle")
        lbl_cap_total.set_halign(Gtk.Align.START)
        lbl_cap_total.set_line_wrap(False)
        box_cap.pack_start(lbl_cap_total, False, False, 0)

        self.card.pack_start(box_cap, False, False, 2)

        self.card.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # --- Velocidade em tempo real ---
        lbl_sec = Gtk.Label(label="Velocidade de I/O em tempo real:")
        lbl_sec.get_style_context().add_class("section-label")
        lbl_sec.set_halign(Gtk.Align.START)
        self.card.pack_start(lbl_sec, False, False, 0)

        grid_io = Gtk.Grid()
        grid_io.set_column_spacing(8)
        grid_io.set_row_spacing(0)
        grid_io.set_column_homogeneous(True)

        r_class = "stat-val-green" if r_mb > 0.05 else "stat-val"
        w_class = "stat-val-green" if w_mb > 0.05 else "stat-val"


        grid_io.attach(self._make_stat_box("⬇  LEITURA", f"{r_mb:.1f} MB/s", r_class), 0, 0, 1, 1)
        grid_io.attach(self._make_stat_box("⬆  GRAVAÇÃO", f"{w_mb:.1f} MB/s", w_class), 1, 0, 1, 1)
        self.card.pack_start(grid_io, False, False, 0)

        # --- Diagnóstico SMART ---
        health = smart.get("health", "Saudável")
        temp = smart.get("temp_c")
        temp_str = f"  •  {temp}°C" if temp else ""
        health_icon = "✔" if health == "Saudável" else "⚠"
        health_class = "stat-val-green" if health == "Saudável" else "stat-val-warn"

        self.card.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)
        smart_box = self._make_stat_box("SAÚDE DO DISCO (SMART)", f"{health_icon} {health}{temp_str}", health_class)
        self.card.pack_start(smart_box, False, False, 0)


class PopupManager:
    """
    Gerencia o ciclo de vida dos pop-ups flyout.
    Garante que:
    - Apenas uma janela de popup existe por vez.
    - A janela anterior é destruída antes de criar a nova.
    - O posicionamento é calculado APÓS o GTK alocar o tamanho real.
    """

    def __init__(self, dock_window, on_kill_app_callback=None):
        self.dock_window = dock_window
        self.on_kill_app_callback = on_kill_app_callback
        self.active_popup = None
        self._outside_monitor_id = None
        self._mouse_outside_ticks = 0
        self._grace_ticks = 0

    def show_popup(self, gauge_type, monitor_data, manual_kill_enabled=False):
        """
        Cria o novo popup, posiciona e exibe na tela ANTES de destruir o anterior.
        Isso elimina completamente qualquer efeito visual de piscar/flicker.
        """
        old_popup = self.active_popup

        popup = None

        if gauge_type == "ram":
            popup = RAMPopupWindow(
                self.dock_window,
                monitor_data,
                on_kill_callback=self.on_kill_app_callback,
                manual_kill_enabled=manual_kill_enabled
            )

        elif gauge_type == "cpu":
            popup = CPUPopupWindow(self.dock_window, monitor_data)

        elif gauge_type.startswith("disk_mp_"):
            # Busca o disco pelo mountpoint (identificador estável)
            mountpoint = gauge_type[8:]  # Remove o prefixo "disk_mp_"
            disks = monitor_data.get("storage", {}).get("disks", [])
            disk_info = next((d for d in disks if d["mountpoint"] == mountpoint), None)
            if disk_info is None and disks:
                disk_info = disks[0]
            if disk_info:
                popup = SingleDiskPopupWindow(self.dock_window, disk_info)

        # Compatibilidade com índice numérico (fallback)
        elif gauge_type.startswith("disk_"):
            idx_str = gauge_type.replace("disk_", "")
            idx = int(idx_str) if idx_str.isdigit() else 0
            disks = monitor_data.get("storage", {}).get("disks", [])
            if disks:
                disk_info = disks[idx] if idx < len(disks) else disks[0]
                popup = SingleDiskPopupWindow(self.dock_window, disk_info)

        if not popup:
            return

        self.active_popup = popup
        self.active_popup.connect("destroy", self._on_popup_closed)

        # 1. Posiciona e exibe a NOVA janela imediatamente
        self._position_popup_window(self.active_popup)
        self.active_popup.show_all()
        self.active_popup.present()

        # 2. Somente agora que a nova está pronta e visível, destrói a antiga
        if old_popup and old_popup != self.active_popup:
            try:
                old_popup.destroy()
            except Exception:
                pass

        # 3. Refinamento de alinhamento com tamanho final alocado
        GLib.idle_add(lambda: self._position_popup_window(self.active_popup) if self.active_popup else False)

        # 4. Monitor de cliques fora e hover leave
        self._mouse_outside_ticks = 0
        self._grace_ticks = 4  # tolerância inicial para o clique de abertura
        if self._outside_monitor_id:
            GLib.source_remove(self._outside_monitor_id)
        self._outside_monitor_id = GLib.timeout_add(40, self._check_outside_interaction)

    def _on_popup_closed(self, closed_window):
        if self.active_popup == closed_window:
            if self._outside_monitor_id:
                GLib.source_remove(self._outside_monitor_id)
                self._outside_monitor_id = None
            self.active_popup = None

    def close_popup(self):
        """Destrói imediatamente o popup ativo."""
        if self._outside_monitor_id:
            GLib.source_remove(self._outside_monitor_id)
            self._outside_monitor_id = None

        if self.active_popup:
            try:
                popup = self.active_popup
                self.active_popup = None  # Limpa antes de destruir para evitar recursão
                popup.destroy()
            except Exception:
                pass

    def is_visible(self):
        return self.active_popup is not None and self.active_popup.get_visible()

    def _check_outside_interaction(self):
        """
        Monitora se o usuário clicou fora da dock/popup ou afastou o mouse.
        Fecha imediatamente o popup se houver clique fora da dock e do popup,
        ou fecha após afastamento prolongado do mouse (hover leave).
        """
        if not self.active_popup or not self.active_popup.get_visible():
            self._outside_monitor_id = None
            return False

        try:
            disp = Gdk.Display.get_default()
            seat = disp.get_default_seat() if disp else None
            pointer = seat.get_pointer() if seat else None
            root = Gdk.get_default_root_window()

            if not pointer or not root:
                return True

            _, px, py, mask = root.get_device_position(pointer)

            # 1. Bounding box do Popup
            pop_x, pop_y = self.active_popup.get_position()
            pop_w, pop_h = self.active_popup.get_size()
            is_in_popup = (pop_x - 4 <= px <= pop_x + pop_w + 4) and (pop_y - 4 <= py <= pop_y + pop_h + 4)

            # 2. Bounding box da Dock
            dock_x, dock_y = self.dock_window.get_position()
            dock_w, dock_h = self.dock_window.get_size()
            is_in_dock = (dock_x - 4 <= px <= dock_x + dock_w + 4) and (dock_y - 4 <= py <= dock_y + dock_h + 4)

            # Tolerância para o momento do clique inicial
            if self._grace_ticks > 0:
                self._grace_ticks -= 1
                return True

            # 3. DETECÇÃO DE CLIQUE FORA (Qualquer botão do mouse pressionado fora de ambos)
            has_click = bool(int(mask) & (int(Gdk.ModifierType.BUTTON1_MASK) | int(Gdk.ModifierType.BUTTON2_MASK) | int(Gdk.ModifierType.BUTTON3_MASK)))

            if has_click and not is_in_popup and not is_in_dock:
                self.close_popup()
                if hasattr(self.dock_window, "on_popup_dismissed"):
                    self.dock_window.on_popup_dismissed()
                return False

            # 4. HOVER LEAVE (Se o mouse saiu de ambos sem clicar, fecha após ~700ms)
            if not is_in_popup and not is_in_dock:
                self._mouse_outside_ticks += 1
                if self._mouse_outside_ticks >= 18:
                    self.close_popup()
                    if hasattr(self.dock_window, "on_popup_dismissed"):
                        self.dock_window.on_popup_dismissed()
                    return False
            else:
                self._mouse_outside_ticks = 0

        except Exception:
            pass

        return True

    def _position_popup_window(self, popup):
        """
        Posiciona a janela do popup ao lado da dock.
        """
        if not popup:
            return False

        # Obtém posição e tamanho da dock
        dock_x, dock_y = self.dock_window.get_position()
        dock_w, dock_h = self.dock_window.get_size()

        # Obtém o tamanho da janela de popup
        popup_w, popup_h = popup.get_size()

        edge = self.dock_window.edge
        margin = 14

        # Calcula posição baseada na borda da dock
        if edge == "right":
            px = dock_x - popup_w - margin
            py = dock_y + max(0, (dock_h - popup_h) // 2)
        elif edge == "left":
            px = dock_x + dock_w + margin
            py = dock_y + max(0, (dock_h - popup_h) // 2)
        elif edge == "top":
            py = dock_y + dock_h + margin
            px = dock_x + max(0, (dock_w - popup_w) // 2)
        else:  # bottom
            py = dock_y - popup_h - margin
            px = dock_x + max(0, (dock_w - popup_w) // 2)

        # Garante que o popup não saia da tela
        geo = self.dock_window._get_target_monitor_geometry() if hasattr(self.dock_window, "_get_target_monitor_geometry") else None
        if not geo:
            display = Gdk.Display.get_default()
            mon = display.get_primary_monitor() or display.get_monitor(0)
            if mon:
                geo = mon.get_geometry()

        if geo:
            px = max(geo.x + 8, min(px, geo.x + geo.width - popup_w - 8))
            py = max(geo.y + 8, min(py, geo.y + geo.height - popup_h - 8))

        popup.move(px, py)
        return False
