"""
ZeroFreeze - Diálogo de Histórico de Intervenções e Picos
Exibe os eventos de salvamento anti-freeze, alertas e processos que subiram de consumo repentinamente.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango
from src.history import get_history_events, clear_history

class HistoryDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(
            title="📜 Histórico de Intervenções & Picos de Memória",
            transient_for=parent,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        )
        self.set_default_size(560, 520)
        self.set_border_width(12)

        content = self.get_content_area()
        content.set_spacing(10)

        lbl_desc = Gtk.Label(
            label="Registro de todas as ações de salvaguarda executadas pelo ZeroFreeze, alertas e processos com saltos bruscos de memória:"
        )
        lbl_desc.set_line_wrap(True)
        lbl_desc.set_halign(Gtk.Align.START)
        content.pack_start(lbl_desc, False, False, 0)

        # ScrolledWindow com a lista de eventos
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(340)

        self.box_events = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        scrolled.add(self.box_events)
        content.pack_start(scrolled, True, True, 0)

        # Barra inferior com Limpar e Fechar
        box_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_clear = Gtk.Button(label="🗑️ Limpar Histórico")
        btn_clear.connect("clicked", self._on_clear)
        box_actions.pack_start(btn_clear, False, False, 0)
        content.pack_start(box_actions, False, False, 0)

        self.add_button("Fechar", Gtk.ResponseType.CLOSE)

        self._refresh_events()
        self.show_all()

    def _refresh_events(self):
        for child in list(self.box_events.get_children()):
            self.box_events.remove(child)

        events = get_history_events(limit=80)
        if not events:
            lbl_empty = Gtk.Label(label="Nenhum evento registrado até o momento.\nO sistema está operando perfeitamente!")
            lbl_empty.set_justify(Gtk.Justification.CENTER)
            lbl_empty.get_style_context().add_class("dim-label")
            self.box_events.pack_start(lbl_empty, True, True, 40)
        else:
            for ev in events:
                ev_type = ev.get("type", "ALERT")
                app_name = ev.get("app_name", "Desconhecido")
                mem_mb = ev.get("memory_mb", 0.0)
                pct = ev.get("percent", 0.0)
                details = ev.get("details", "")
                ts = ev.get("timestamp", "")

                card = Gtk.Frame()
                card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
                card_box.set_border_width(8)
                card.add(card_box)

                # Cabeçalho da linha
                row_head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

                if ev_type == "KILL":
                    icon_tag = "🛑 <b>[INTERVENÇÃO]</b>"
                    color_tag = "#ff4444"
                elif ev_type == "SPIKE":
                    icon_tag = "📈 <b>[PICO ANORMAL]</b>"
                    color_tag = "#ffaa00"
                else:
                    icon_tag = "⚠️ <b>[ALERTA 90%]</b>"
                    color_tag = "#ffcc00"

                lbl_tag = Gtk.Label(label=f"<span foreground='{color_tag}'>{icon_tag}</span>  <b>{app_name}</b> ({mem_mb:.0f} MB / {pct}%)")
                lbl_tag.set_use_markup(True)
                lbl_tag.set_halign(Gtk.Align.START)
                row_head.pack_start(lbl_tag, True, True, 0)

                lbl_time = Gtk.Label(label=f"<small>{ts}</small>")
                lbl_time.set_use_markup(True)
                lbl_time.get_style_context().add_class("dim-label")
                row_head.pack_start(lbl_time, False, False, 0)

                card_box.pack_start(row_head, False, False, 0)

                if details:
                    lbl_det = Gtk.Label(label=f"<small>{details}</small>")
                    lbl_det.set_use_markup(True)
                    lbl_det.set_halign(Gtk.Align.START)
                    lbl_det.get_style_context().add_class("dim-label")
                    card_box.pack_start(lbl_det, False, False, 0)

                self.box_events.pack_start(card, False, False, 0)

        self.box_events.show_all()

    def _on_clear(self, widget):
        clear_history()
        self._refresh_events()
