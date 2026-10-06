"""
ZeroFreeze - Widget de Medidor Radial Circular (Cairo)
Desenha anéis de progresso com porcentagem e ícone central, próximo à referência visual.
Visual: fundo preto profundo, anel espesso, ícone branco central, % abaixo.
"""

import math
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GObject, Pango, PangoCairo


def get_gauge_ring_color(percent):
    """
    Calcula a cor dinâmica padrão dos aros com base nas faixas estipuladas pelo Linker:
    - até 50%: Verde
    - 50% a 60%: Transição suave do Verde para o Amarelo
    - 61% a 85%: Amarelo
    - 85% a 90%: Transição suave do Amarelo para o Vermelho
    - 91% a 100%: Vermelho
    """
    c_green = (0.15, 0.85, 0.35)
    c_yellow = (0.98, 0.82, 0.10)
    c_red = (0.95, 0.18, 0.20)

    p = max(0.0, min(100.0, float(percent)))

    if p <= 50.0:
        return c_green
    elif p <= 60.0:
        # Interpolação Verde -> Amarelo
        t = (p - 50.0) / 10.0
        return (
            c_green[0] + (c_yellow[0] - c_green[0]) * t,
            c_green[1] + (c_yellow[1] - c_green[1]) * t,
            c_green[2] + (c_yellow[2] - c_green[2]) * t,
        )
    elif p <= 85.0:
        return c_yellow
    elif p <= 90.0:
        # Interpolação Amarelo -> Vermelho
        t = (p - 85.0) / 5.0
        return (
            c_yellow[0] + (c_red[0] - c_yellow[0]) * t,
            c_yellow[1] + (c_red[1] - c_yellow[1]) * t,
            c_yellow[2] + (c_red[2] - c_yellow[2]) * t,
        )
    else:
        return c_red


class RadialGauge(Gtk.EventBox):
    __gsignals__ = {
        'gauge-clicked': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'gauge-hovered': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, title, icon_symbol, default_color=(0.2, 0.7, 1.0), size=54):
        super().__init__()
        self.set_visible_window(False)
        self.set_above_child(True)
        self.title = title
        self.icon_symbol = icon_symbol
        self.default_color = default_color  # RGB float tuple (0.0 - 1.0)
        self.percent = 0.0
        self.size = size
        self.is_hovered = False

        # Área de desenho: o anel + texto de porcentagem embaixo
        self.area = Gtk.DrawingArea()
        self._update_area_size()
        self.area.connect("draw", self.on_draw)
        self.add(self.area)

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        self.connect("button-press-event", self.on_click)
        self.connect("enter-notify-event", self.on_enter)
        self.connect("leave-notify-event", self.on_leave)

    def _update_area_size(self):
        extra_h = max(14, int(22 * (self.size / 54.0)))
        extra_w = max(4, int(8 * (self.size / 54.0)))
        self.area.set_size_request(self.size + extra_w, self.size + extra_h)

    def set_size(self, new_size):
        """Atualiza a escala de tamanho do medidor."""
        if self.size != new_size:
            self.size = new_size
            self._update_area_size()
            self.area.queue_resize()
            self.area.queue_draw()

    def set_percent(self, val):
        val = max(0.0, min(100.0, float(val)))
        if abs(self.percent - val) > 0.4:
            self.percent = val
            self.area.queue_draw()

    def on_click(self, widget, event):
        if event.button == 1:
            self.emit('gauge-clicked')
            return True
        return False

    def on_enter(self, widget, event):
        self.is_hovered = True
        self.area.queue_draw()
        self.emit('gauge-hovered')
        return False

    def on_leave(self, widget, event):
        self.is_hovered = False
        self.area.queue_draw()
        return False

    def on_draw(self, widget, cr):
        width = self.area.get_allocated_width()
        height = self.area.get_allocated_height()

        scale_factor = max(0.35, self.size / 54.0)

        cx = width / 2.0
        cy = (self.size / 2.0) + (3.0 * scale_factor)
        radius = max(6.0, (self.size / 2.0) - (6.0 * scale_factor))
        line_width = max(2.5, 6.0 * scale_factor)

        # --- 1. Prato de fundo circular (disco escuro sob o anel) ---
        disc_radius = radius + (7.0 * scale_factor)
        cr.arc(cx, cy, disc_radius, 0, 2 * math.pi)
        if self.is_hovered:
            cr.set_source_rgba(0.18, 0.20, 0.25, 0.97)
        else:
            cr.set_source_rgba(0.10, 0.11, 0.14, 0.95)
        cr.fill()

        # Borda muito sutil do prato
        cr.arc(cx, cy, disc_radius, 0, 2 * math.pi)
        cr.set_source_rgba(0.40, 0.43, 0.50, 0.35)
        cr.set_line_width(max(0.6, 1.0 * scale_factor))
        cr.stroke()

        # --- 2. Trilho do anel (faixa cinza inativa) ---
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.set_source_rgba(0.22, 0.24, 0.28, 0.70)
        cr.set_line_width(line_width)
        cr.stroke()

        # --- 3. Cor dinâmica do anel de progresso ---
        r, g, b = get_gauge_ring_color(self.percent)

        # Cor configurada pelo usuário exclusivamente para o ícone central
        icon_r, icon_g, icon_b = self.default_color

        # --- 4. Arco de progresso ativo ---
        start_angle = -math.pi / 2.0     # Começa no topo (posição 12h)
        progress_angle = (self.percent / 100.0) * (2 * math.pi)
        end_angle = start_angle + progress_angle

        if self.percent > 0.5:
            cr.arc(cx, cy, radius, start_angle, end_angle)
            cr.set_source_rgba(r, g, b, 0.97)
            cr.set_line_width(line_width)
            cr.set_line_cap(1)  # Cairo.LineCap.ROUND
            cr.stroke()

        # --- 5. Ícone central vetorial com a cor personalizada do usuário ---
        self._draw_center_icon(cr, cx, cy, icon_r, icon_g, icon_b, scale=scale_factor)

        # --- 6. Texto de porcentagem abaixo do anel (acompanha cor do anel) ---
        text_pct = f"{int(round(self.percent))}%"
        cr.select_font_face("Sans", 0, 1)  # Normal, Bold
        cr.set_font_size(max(6.5, 10.0 * scale_factor))
        cr.set_source_rgba(r, g, b, 1.0)
        extents = cr.text_extents(text_pct)
        tx = cx - (extents[2] / 2.0) - extents[0]
        ty = cy + disc_radius + (12.0 * scale_factor)
        cr.move_to(tx, ty)
        cr.show_text(text_pct)

        return False

    def _draw_center_icon(self, cr, cx, cy, icon_r, icon_g, icon_b, scale=1.0):
        """Delega o desenho para as funções externas editáveis em src/ui/icons.py."""
        from src.ui import icons

        if self.title == "RAM":
            icons.draw_ram_icon(cr, cx, cy, icon_r, icon_g, icon_b, scale=scale)
        elif self.title == "CPU":
            icons.draw_cpu_icon(cr, cx, cy, icon_r, icon_g, icon_b, scale=scale)
        else:
            icons.draw_disk_icon(cr, cx, cy, icon_r, icon_g, icon_b, scale=scale)

