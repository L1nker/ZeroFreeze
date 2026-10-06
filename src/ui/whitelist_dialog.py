"""
ZeroFreeze - Diálogo de Gerenciamento da Lista Branca (Whitelist)
Permite visualizar, adicionar, remover e selecionar aplicativos em execução para proteção.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango

class WhitelistDialog(Gtk.Dialog):
    def __init__(self, parent, config_manager, monitor, on_changed_callback=None):
        super().__init__(
            title="🛡️ Lista Branca de Aplicativos Protegidos",
            transient_for=parent,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        )
        self.config_mgr = config_manager
        self.monitor = monitor
        self.on_changed = on_changed_callback

        self.set_default_size(520, 560)
        self.set_border_width(12)

        content = self.get_content_area()
        content.set_spacing(10)

        # Cabeçalho explicativo
        lbl_info = Gtk.Label(
            label="Os aplicativos cadastrados nesta lista <b>nunca</b> serão encerrados pela salvaguarda anti-travamento, mesmo em situações extremas de memória."
        )
        lbl_info.set_use_markup(True)
        lbl_info.set_line_wrap(True)
        lbl_info.set_halign(Gtk.Align.START)
        content.pack_start(lbl_info, False, False, 0)

        # Botão de Ação Rápida: Ler programas abertos
        btn_scan = Gtk.Button(label="🔍 Selecionar dos Aplicativos Abertos no Momento")
        btn_scan.get_style_context().add_class("suggested-action")
        btn_scan.connect("clicked", self._open_running_apps_picker)
        content.pack_start(btn_scan, False, False, 4)

        # Lista de itens protegidos
        frame_list = Gtk.Frame(label="Aplicativos Atualmente Protegidos:")
        box_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box_frame.set_border_width(8)
        frame_list.add(box_frame)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_min_content_height(260)

        self.box_items = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.scrolled.add(self.box_items)
        box_frame.pack_start(self.scrolled, True, True, 0)

        content.pack_start(frame_list, True, True, 0)

        # Adicionar item manualmente
        box_manual = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.entry_manual = Gtk.Entry()
        self.entry_manual.set_placeholder_text("Nome do processo (ex: anydesk, steam, vlc)...")
        self.entry_manual.connect("activate", self._on_add_manual)
        btn_add_manual = Gtk.Button(label="➕ Adicionar")
        btn_add_manual.connect("clicked", self._on_add_manual)

        box_manual.pack_start(self.entry_manual, True, True, 0)
        box_manual.pack_start(btn_add_manual, False, False, 0)
        content.pack_start(box_manual, False, False, 0)

        # Botão Fechar
        self.add_button("Fechar", Gtk.ResponseType.CLOSE)

        self._refresh_list()
        self.show_all()

    def _get_whitelist(self):
        return list(self.config_mgr.get("safety", "whitelist", []))

    def _refresh_list(self):
        for child in list(self.box_items.get_children()):
            self.box_items.remove(child)

        wlist = self._get_whitelist()
        if not wlist:
            lbl_empty = Gtk.Label(label="Nenhum aplicativo personalizado na lista branca.")
            lbl_empty.get_style_context().add_class("dim-label")
            self.box_items.pack_start(lbl_empty, True, True, 20)
        else:
            for item in sorted(wlist, key=lambda s: s.lower()):
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                row.set_margin_start(4)
                row.set_margin_end(4)

                lbl = Gtk.Label(label=f"🛡️  <b>{item}</b>")
                lbl.set_use_markup(True)
                lbl.set_halign(Gtk.Align.START)
                row.pack_start(lbl, True, True, 0)

                # Sistema essencial não pode ser removido pelo usuário
                is_system = item.lower() in ["zerofreeze", "python3", "gnome-shell", "cinnamon", "systemd", "xorg"]
                if not is_system:
                    btn_del = Gtk.Button(label="🗑️ Remover")
                    btn_del.connect("clicked", lambda w, s=item: self._remove_item(s))
                    row.pack_start(btn_del, False, False, 0)
                else:
                    lbl_sys = Gtk.Label(label="[Sistema]")
                    lbl_sys.get_style_context().add_class("dim-label")
                    row.pack_start(lbl_sys, False, False, 0)

                self.box_items.pack_start(row, False, False, 2)

        self.box_items.show_all()

    def _remove_item(self, item_name):
        wlist = self._get_whitelist()
        wlist = [x for x in wlist if x.lower() != item_name.lower()]
        self.config_mgr.set("safety", "whitelist", wlist)
        self.config_mgr.save()
        if self.on_changed:
            self.on_changed()
        self._refresh_list()

    def _on_add_manual(self, *args):
        text = self.entry_manual.get_text().strip()
        if text:
            wlist = self._get_whitelist()
            if not any(x.lower() == text.lower() for x in wlist):
                wlist.append(text)
                self.config_mgr.set("safety", "whitelist", wlist)
                self.config_mgr.save()
                if self.on_changed:
                    self.on_changed()
            self.entry_manual.set_text("")
            self._refresh_list()

    def _open_running_apps_picker(self, widget):
        """Abre janela para selecionar dentre os processos ativos no sistema."""
        dlg = Gtk.Dialog(
            title="Selecionar dos Aplicativos em Execução",
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        )
        dlg.set_default_size(440, 480)
        dlg.set_border_width(10)

        box = dlg.get_content_area()
        box.set_spacing(8)

        lbl = Gtk.Label(label="Marque os aplicativos que você deseja proteger contra encerramento:")
        lbl.set_halign(Gtk.Align.START)
        box.pack_start(lbl, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(340)

        box_apps = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scrolled.add(box_apps)
        box.pack_start(scrolled, True, True, 0)

        # Varre processos abertos
        top_apps = self.monitor.get_top_memory_apps(limit=30)
        current_wlist = set(x.lower() for x in self._get_whitelist())

        checks = []
        for app in top_apps:
            name = app["name"]
            raw_name = app["raw_name"]
            mem_mb = app.get("memory_mb", 0.0)

            # Ignora o próprio ZeroFreeze e raiz
            if name.lower() in ["zerofreeze", "python3", "systemd"]:
                continue

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            chk = Gtk.CheckButton(label=f"{name} ({mem_mb:.0f} MB)")
            chk.set_active(raw_name.lower() in current_wlist or name.lower() in current_wlist)
            row.pack_start(chk, True, True, 0)

            box_apps.pack_start(row, False, False, 2)
            checks.append((chk, raw_name, name))

        dlg.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        btn_apply = dlg.add_button("Salvar Selecionados", Gtk.ResponseType.OK)
        btn_apply.get_style_context().add_class("suggested-action")

        dlg.show_all()
        response = dlg.run()

        if response == Gtk.ResponseType.OK:
            wlist = self._get_whitelist()
            wlist_set = set(x.lower() for x in wlist)

            for chk, raw_name, friendly_name in checks:
                target_key = raw_name
                if chk.get_active():
                    if target_key.lower() not in wlist_set and friendly_name.lower() not in wlist_set:
                        wlist.append(target_key)
                else:
                    wlist = [x for x in wlist if x.lower() not in (raw_name.lower(), friendly_name.lower())]

            self.config_mgr.set("safety", "whitelist", wlist)
            self.config_mgr.save()
            if self.on_changed:
                self.on_changed()
            self._refresh_list()

        dlg.destroy()
