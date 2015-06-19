from gi.repository import Gtk, Gio, GdkPixbuf
from globals import *


class Window(Gtk.ApplicationWindow):

    def __init__(self, epub):
        self.widgets = None
        self.liststore = None
        self.popover = None
        self.calendar = None
        self.epub = epub

        Gtk.ApplicationWindow.__init__(self)

        builder = Gtk.Builder()
        builder.add_from_file('headerbar.xml')
        self.set_titlebar(builder.get_object('headerbar'))

        builder.get_object('more_button').grab_focus()

        self.connect('delete-event', self.quit)
        self.set_title(self.epub.file_path)

        self.widgets = Gtk.Builder()
        self.widgets.add_from_file('widgets.xml')

        self.add(self.widgets.get_object('box1'))

        self.populate_tags_list()
        self.populate_fields()
        self.set_cover_image()
        self.create_calendar_popover()

        self.show_all()

    def populate_fields(self):
        self.widgets.get_object('title_entry').set_text(self.epub.title)
        self.widgets.get_object('author_entry').set_text(self.epub.author)
        self.widgets.get_object('publisher_entry').set_text(self.epub.publisher)
        self.widgets.get_object('date_entry').set_text(self.epub.date)

    def populate_tags_list(self):
        self.liststore = Gtk.ListStore(str)

        for item in self.epub.fields:
            if item.tag == '{}subject'.format(DC_NAMESPACE):
                self.liststore.append([item.text])

        self.widgets.get_object('treeview').set_model(self.liststore)

        renderer = Gtk.CellRendererText()
        renderer.set_property('editable', True)

        column = Gtk.TreeViewColumn('Tags', renderer, text=0)
        self.widgets.get_object('treeview').append_column(column)

        renderer.connect('edited', self.text_edited)

    def create_calendar_popover(self):
        self.popover = Gtk.Popover()
        self.popover.set_relative_to(self.widgets.get_object('date_entry'))
        self.widgets.get_object('date_entry').connect('icon-press', self.toggle_calendar)

        self.calendar = Gtk.Calendar()
        self.popover.add(self.calendar)

    def toggle_calendar(self, widget, icon, event):
        if self.popover.get_visible():
            self.popover.hide()
        else:
            self.popover.show_all()

    def set_cover_image(self):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.epub.temp_cover, -1, 400, True)
        self.widgets.get_object('cover_image').set_from_pixbuf(pixbuf)

    def text_edited(self, widget, path, text):
        if not len(text):
            self.liststore.remove(self.liststore.get_iter(path))
        else:
            self.liststore[path][0] = text

    def quit(self, event, user_data):
        del self.epub
        Gtk.main_quit()
