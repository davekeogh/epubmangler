# -*- coding: utf-8 -*-

from gi.repository import Gtk, Gdk, Gio, GdkPixbuf, GObject, WebKit2
from globals import *
from util import *

import os, os.path


class Window(Gtk.ApplicationWindow):

    def __init__(self, epub):
        self.widgets = None
        self.header_widgets = None
        self.menu_widgets = None
        self.menu = None
        self.image = None
        self.image_size = None
        self.popover = None
        self.calendar = None
        self.web_view = None
        self.epub = epub
        self.liststore = Gtk.ListStore(str)

        Gtk.ApplicationWindow.__init__(self)

        self.header_widgets = Gtk.Builder()
        self.header_widgets.add_from_file('headerbar.xml')
        self.set_titlebar(self.header_widgets.get_object('headerbar'))

        self.menu_widgets = Gtk.Builder()
        self.menu_widgets.add_from_file('menu.xml')

        self.connect('delete-event', self.quit)
        
        self.set_title(self.epub.name)
        self.set_icon_name(ICON_NAME)

        self.widgets = Gtk.Builder()
        self.widgets.add_from_file('widgets.xml')

        self.add(self.widgets.get_object('box1'))
        self.widgets.get_object('box1').set_property('expand', True)

        self.image = self.widgets.get_object('cover_image')
        self.connect('configure-event', self.resize_image)

        self.populate_tags_list()
        self.populate_fields()
        self.populate_files_tree()
        self.render_description_html()
        self.set_cover_image()
        self.create_calendar_popover()
        self.create_menu_popover()

        self.widgets.get_object('series_entry').connect('changed', self.toggle_series_index_spinbutton)
        self.widgets.get_object('tags_entry').connect('changed', self.toggle_tags_add_button)
        self.widgets.get_object('tags_entry').connect('activate', self.add_tag)
        self.widgets.get_object('tags_entry').connect('icon_press', self.add_tag)
        self.widgets.get_object('infobar').connect('response', self.toggle_infobar)

        self.show_all()

    def populate_fields(self):
        self.widgets.get_object('title_entry').set_text(self.epub.title)
        self.widgets.get_object('author_entry').set_text(self.epub.author)
        self.widgets.get_object('publisher_entry').set_text(self.epub.publisher)
        self.widgets.get_object('date_entry').set_text(self.epub.get_date_as_string())
        self.widgets.get_object('series_entry').set_text(self.epub.series)
        self.widgets.get_object('series_spinbutton').set_value(self.epub.series_index)

        if self.epub.debug_information:
            buf = Gtk.TextBuffer()
            buf.set_text(self.epub.debug_information)
            self.widgets.get_object('textview1').set_buffer(buf)
        else:
            self.widgets.get_object('notebook').remove_page(3)

        self.toggle_series_index_spinbutton(self.widgets.get_object('series_entry'))
        self.toggle_tags_add_button(self.widgets.get_object('tags_entry'))

    def populate_files_tree(self):
        tree = self.widgets.get_object('treeview2')
        model = Gtk.TreeStore(str, int)
        model.set_sort_func(0, sortfunc)
        model.set_sort_column_id(0, Gtk.SortType.DESCENDING)

        dirwalk(model, self.epub.temp_dir)

        tree.set_model(model)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Files', renderer, text=0)

        tree.append_column(column)

    def render_description_html(self):
        self.web_view = WebKit2.WebView()

        overlay = self.widgets.get_object('overlay1')
        overlay.add(self.web_view)

        box = Gtk.Box(Gtk.Orientation.HORIZONTAL)
        box.set_spacing(0)
        
        image = Gtk.Image.new_from_icon_name('document-properties-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
        label = Gtk.Label('')
        box.add(image)
        box.add(label)
        
        button = Gtk.Button()
        button.add(box)
        button.set_valign(Gtk.Align.START)
        button.set_halign(Gtk.Align.END)
        button.set_margin_top(10)
        button.set_margin_right(20)
        button.set_opacity(0.75)
        
        button.connect('enter-notify-event', self.button_mouse_over)
        button.connect('leave-notify-event', self.button_mouse_over)

        overlay.add_overlay(button)

        self.web_view.load_html(HTML_TEMPLATE.format(description=self.epub.description))
    
    def button_mouse_over(self, widget, event):
        label = widget.get_children()[0].get_children()[1]
        
        if event.type == Gdk.EventType.ENTER_NOTIFY:
            widget.set_opacity(1)
            widget.get_children()[0].set_spacing(5)
            label.set_text('Edit description')
            
        elif event.type == Gdk.EventType.LEAVE_NOTIFY:
            widget.set_opacity(0.75)
            label.set_text('')
    
    def populate_tags_list(self):
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
        self.calendar.select_month(self.epub.date.tm_mon - 1, self.epub.date.tm_year)
        self.calendar.select_day(self.epub.date.tm_mday)

        self.calendar.connect('month-changed', self.calendar_changed)
        self.calendar.connect('day-selected', self.calendar_changed)
        self.calendar.connect('next-year', self.calendar_changed)
        self.calendar.connect('prev-year', self.calendar_changed)
        self.popover.connect('closed', self.calendar_changed_then_toggle)

        self.popover.add(self.calendar)

    def create_menu_popover(self):
        self.menu = self.menu_widgets.get_object('menu')
        self.menu.set_relative_to(self.header_widgets.get_object('more_button'))
        self.header_widgets.get_object('more_button').connect('pressed', self.toggle_menu)

        self.menu_widgets.get_object('about_menu').connect('clicked', self.show_about_dialog)
        self.menu_widgets.get_object('quit_menu').connect('clicked', self.quit)

    def show_about_dialog(self, widget):
        dialog = Gtk.AboutDialog()
        dialog.set_program_name('Epub Mangler')
        dialog.set_logo_icon_name(ICON_NAME)
        dialog.set_version('0.10')
        dialog.set_copyright('Copyright © 2016-2017 David Keogh')
        dialog.set_license_type(Gtk.License.GPL_3_0)
        dialog.set_comments('A program to modify ebook files')
        dialog.set_website('https://github.com/davekeogh/epubmangler')
        dialog.set_transient_for(self)
        
        result = dialog.run()

        if result:
            dialog.destroy()

    def calendar_changed(self, widget):
        date = self.calendar.get_date()
        self.widgets.get_object('date_entry').set_text('{} - {} - {}'.format(date[0], date[1] + 1, date[2]))

    def toggle_calendar(self, widget, icon, event):
        if self.popover.get_visible():
            self.widgets.get_object('date_entry').set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY,
                                                                          'go-down-symbolic')
            self.popover.hide()
        else:
            self.widgets.get_object('date_entry').set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY,
                                                                          'go-up-symbolic')
            self.popover.show_all()

    def toggle_menu(self, widget):
        if self.menu.get_visible():
            self.menu.hide()
        else:
            self.menu.show_all()

    def calendar_changed_then_toggle(self, widget):
        self.calendar_changed(self.calendar)
        self.toggle_calendar(self, None, None)

    def set_cover_image(self, x=-1, y=500):
        if os.path.isfile(self.epub.temp_cover):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.epub.temp_cover, x, y, True)
            self.image.set_from_pixbuf(pixbuf)

        allocation = self.image.get_allocation()
        self.image_size = (allocation.height, allocation.width)

    def resize_image(self, widget, event):
        allocation = self.image.get_allocation()

        if allocation.width != self.image_size[0] or allocation.height != self.image_size[1]:
            self.set_cover_image(x=allocation.width, y=allocation.height)

    def text_edited(self, widget, path, text):
        if not len(text):
            self.liststore.remove(self.liststore.get_iter(path))
        else:
            self.liststore[path][0] = text

    def add_tag(self, widget, icon=None, event=None):
        text = widget.get_text()
        widget.set_text('')

        if len(text) > 1:
            for row in self.liststore:
                if row[0] == text:
                    return

            tree_iter = self.liststore.append()
            self.liststore.set_value(tree_iter, 0, text)

    def toggle_series_index_spinbutton(self, entry):
        if not len(entry.get_text()):
            self.widgets.get_object('series_spinbutton').set_sensitive(False)
        else:
            self.widgets.get_object('series_spinbutton').set_sensitive(True)

    def toggle_infobar(self, widget, response=None):
        if self.widgets.get_object('revealer').get_child_revealed():
            self.widgets.get_object('revealer').set_reveal_child(False)
        else:
            self.widgets.get_object('revealer').set_reveal_child(True)

    def toggle_tags_add_button(self, entry):
        if not len(entry.get_text()):
            entry.set_icon_sensitive(Gtk.EntryIconPosition.SECONDARY, False)
        else:
            entry.set_icon_sensitive(Gtk.EntryIconPosition.SECONDARY, True)

    def export(self, target=None):
        if not target:
            target = self.epub

        target.title = self.widgets.get_object('title_entry').get_text()
        target.author = self.widgets.get_object('author_entry').get_text()
        target.series = self.widgets.get_object('series_entry').get_text()
        target.series_index = self.widgets.get_object('series_spinbutton').get_value()

        target.set_date_for_export(self.widgets.get_object('date_entry').get_text())

        tags = []

        for row in self.liststore:
            tags.append(row[0])

        target.update_tags(tags)
        target.update_fields()

    def quit(self, event, user_data=None):
        del self.epub
        Gtk.main_quit()
