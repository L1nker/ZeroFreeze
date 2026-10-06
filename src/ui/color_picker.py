"""
ZeroFreeze - Ferramenta de Conta-gotas de Alta Precisão (Screen Color Dropper)
Permite ao usuário capturar qualquer cor na tela inteira com preview instantâneo em tempo real.
Utiliza captura única em memória e Seat Grab de ponteiro para ativação instantânea no primeiro clique.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib


class ScreenEyedropper(Gtk.Window):
    def __init__(self, on_color_selected_callback, parent_window=None):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.on_color_selected = on_color_selected_callback
        self.parent_window = parent_window
        self._cleaned_up = False
        self.seat = None

        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_app_paintable(True)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        # Oculta temporariamente a janela pai para desimpedir a visão total da tela
        if self.parent_window:
            try:
                self.parent_window.hide()
                while Gtk.events_pending():
                    Gtk.main_iteration()
            except Exception:
                pass

        # Captura instantânea da tela inteira congelada como Pixbuf na memória
        root = Gdk.get_default_root_window()
        self.total_w = root.get_width()
        self.total_h = root.get_height()

        try:
            self.pix = Gdk.pixbuf_get_from_window(root, 0, 0, self.total_w, self.total_h)
            self.pixels = self.pix.get_pixels()
            self.rowstride = self.pix.get_rowstride()
            self.n_channels = self.pix.get_n_channels()
        except Exception as e:
            print(f"[ZeroFreeze] Erro na captura de tela do conta-gotas: {e}")
            self.pix = None
            self.pixels = None

        self.set_default_size(self.total_w, self.total_h)
        self.move(0, 0)

        # Posição inicial do ponteiro
        display = Gdk.Display.get_default()
        device_manager = display.get_device_manager()
        pointer = device_manager.get_client_pointer()
        _, init_x, init_y = pointer.get_position()
        self.cur_x = init_x
        self.cur_y = init_y
        self.sample_r = 0.0
        self.sample_g = 0.0
        self.sample_b = 0.0
        self._sample_color_at(self.cur_x, self.cur_y)

        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.KEY_PRESS_MASK
        )

        self.connect("draw", self.on_draw)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("button-press-event", self.on_click)
        self.connect("key-press-event", self.on_key)
        self.connect("map-event", self.on_mapped)

        self.show_all()

    def on_mapped(self, widget, event):
        """Ao mapear na tela, realiza o Grab exclusivo do mouse para capturar o primeiro clique."""
        GLib.idle_add(self._do_grab)
        return False

    def _do_grab(self):
        if self._cleaned_up:
            return False
        win = self.get_window()
        if not win:
            return False

        display = Gdk.Display.get_default()
        self.seat = display.get_default_seat()
        cursor = Gdk.Cursor.new_from_name(display, "crosshair")

        status = self.seat.grab(win, Gdk.SeatCapabilities.ALL_POINTING, True, cursor, None, None)
        if status != Gdk.GrabStatus.SUCCESS:
            # Fallback caso o seat grab encontre resistência
            Gdk.pointer_grab(
                win, True,
                Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK,
                None, cursor, Gdk.CURRENT_TIME
            )
        return False

    def _sample_color_at(self, x, y):
        """Lê os valores RGB do pixel na memória em nanossegundos (sem chamadas X11)."""
        if not self.pixels:
            return
        if 0 <= x < self.total_w and 0 <= y < self.total_h:
            offset = y * self.rowstride + x * self.n_channels
            self.sample_r = self.pixels[offset] / 255.0
            self.sample_g = self.pixels[offset + 1] / 255.0
            self.sample_b = self.pixels[offset + 2] / 255.0

    def on_motion(self, widget, event):
        self.cur_x = int(event.x_root)
        self.cur_y = int(event.y_root)
        self._sample_color_at(self.cur_x, self.cur_y)
        self.queue_draw()
        return True

    def on_click(self, widget, event):
        if event.button == 1:  # Botão esquerdo: confirma a seleção
            r, g, b = self.sample_r, self.sample_g, self.sample_b
            self._cleanup()
            if self.on_color_selected:
                self.on_color_selected(r, g, b)
            return True
        elif event.button == 3:  # Botão direito: cancela
            self._cleanup()
            return True
        return False

    def on_key(self, widget, event):
        if event.keyval in [Gdk.KEY_Escape, Gdk.KEY_Return, Gdk.KEY_space]:
            if event.keyval in [Gdk.KEY_Return, Gdk.KEY_space]:
                r, g, b = self.sample_r, self.sample_g, self.sample_b
                self._cleanup()
                if self.on_color_selected:
                    self.on_color_selected(r, g, b)
            else:
                self._cleanup()
            return True
        return False

    def _cleanup(self):
        """Libera o grab do mouse e restaura a janela pai com segurança."""
        if self._cleaned_up:
            return
        self._cleaned_up = True

        try:
            if self.seat:
                self.seat.ungrab()
        except Exception:
            pass

        try:
            Gdk.pointer_ungrab(Gdk.CURRENT_TIME)
        except Exception:
            pass

        if self.parent_window:
            try:
                self.parent_window.show()
                self.parent_window.present()
            except Exception:
                pass

        self.destroy()

    def on_draw(self, widget, cr):
        width = self.get_allocated_width()
        height = self.get_allocated_height()

        # Fundo completamente transparente
        cr.set_operator(0)  # CLEAR
        cr.paint()
        cr.set_operator(2)  # OVER

        # Caixa flutuante de preview ao lado da mira do cursor
        badge_w = 148
        badge_h = 40
        bx = self.cur_x + 18
        by = self.cur_y + 18

        # Reposicionamento inteligente para não sair dos limites da tela
        if bx + badge_w > width:
            bx = self.cur_x - badge_w - 18
        if by + badge_h > height:
            by = self.cur_y - badge_h - 18

        # Fundo do balão flutuante com cantos arredondados
        cr.set_source_rgba(0.06, 0.08, 0.11, 0.95)
        self._draw_rounded_rect(cr, bx, by, badge_w, badge_h, 8)
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.2)
        cr.set_line_width(1.0)
        cr.stroke()

        # Quadrado com a cor capturada
        cr.set_source_rgb(self.sample_r, self.sample_g, self.sample_b)
        self._draw_rounded_rect(cr, bx + 7, by + 7, 26, 26, 4)
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.4)
        cr.set_line_width(1.0)
        cr.stroke()

        # Código HEX em destaque
        hex_code = f"#{int(self.sample_r*255):02X}{int(self.sample_g*255):02X}{int(self.sample_b*255):02X}"
        cr.set_source_rgb(0.95, 0.95, 0.98)
        cr.select_font_face("Monospace", 0, 1)
        cr.set_font_size(12.0)
        cr.move_to(bx + 40, by + 20)
        cr.show_text(hex_code)

        # Instrução explicativa
        cr.set_source_rgba(0.65, 0.72, 0.8, 0.85)
        cr.select_font_face("Sans", 0, 0)
        cr.set_font_size(9.0)
        cr.move_to(bx + 40, by + 32)
        cr.show_text("Clique para capturar")

        return False

    def _draw_rounded_rect(self, cr, x, y, w, h, r):
        import math
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
