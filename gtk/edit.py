#!/usr/bin/env python
"""A GTK interface to the epubmangler library."""

import json
import mimetypes
import os
import random
import sys
import time

from pathlib import Path
from xml.etree.ElementTree import Element

from epubmangler import (EPub, EPubError, sizeof_format, strip_namespace, strip_namespaces,
                         IMAGE_TYPES, NAMESPACES, VERSION, TIME_FORMAT, WEBSITE, XPATHS)

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

# TODO: This needs to get set during install
RESOURCE_DIR = Path('/home/david/Projects/epubmangler/gtk')
BUILDER = str(RESOURCE_DIR / 'widgets.xml')
ICON = str(RESOURCE_DIR / 'epubmangler.svg')


class Application:

    book: EPub
    builder: Gtk.Builder = Gtk.Builder.new_from_file(BUILDER)
    details: Gtk.ListStore = Gtk.ListStore(str, str, str)
    subjects: Gtk.ListStore = Gtk.ListStore(str)
    tags: Gtk.Window = Gtk.ListStore(str)
    config: Path = None
    warnings: bool = True
    mtime_cache: float = 0

    def __init__(self, filename: str) -> None:
        self.book = EPub(filename)
        self.get = self.builder.get_object
        self.window = self.get('window')
        self.window.set_title(Path(self.book.file).name)
        self.window.set_icon_from_file(ICON)

        self.get('title_label').set_text(Path(self.book.file).name)
        self.get('filesize_label').set_text(sizeof_format(self.book.file))
        self.get('version_label').set_text("EPub Version " + self.book.version)

        # Subjects list
        self.get('subjects').set_model(self.subjects)
        self.get('subjects').append_column(Gtk.TreeViewColumn('Subjects',
                                           Gtk.CellRendererText(), text=0))

        # Details view
        self.details.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.get('details').set_model(self.details)

        cell = Gtk.CellRendererText()
        cell.set_property('editable', True)
        cell.connect('edited', self.cell_edited, 0)

        column = Gtk.TreeViewColumn('Tag', cell, text=0)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_sort_column_id(0)
        self.get('details').append_column(column)

        cell = Gtk.CellRendererText()
        cell.set_property('editable', True)
        cell.connect('edited', self.cell_edited, 1)

        column = Gtk.TreeViewColumn('Text', cell, text=1)
        column.set_min_width(self.get('details').get_allocation().width * 0.6)
        column.set_sort_column_id(1)
        self.get('details').append_column(column)

        cell = Gtk.CellRendererText()
        cell.set_property('editable', True)
        cell.set_property('ellipsize', Pango.EllipsizeMode.END)
        cell.connect('edited', self.cell_edited, 2)

        column = Gtk.TreeViewColumn('Attributes', cell, text=2)
        column.set_expand(True)
        self.get('details').append_column(column)

        # Complete tags from the XPATHS dict
        [self.tags.append([key]) for key in XPATHS.keys()]
        tag_completion = Gtk.EntryCompletion()
        tag_completion.set_model(self.tags)
        tag_completion.set_text_column(0)
        self.get('tag_entry').set_completion(tag_completion)

        # Description
        try:
            description_text = self.book.get('description').text
        except EPubError:
            description_text = None

        buffer = self.get('description').get_buffer()

        if description_text:
            buffer.set_text(description_text)

        # Signal connection
        buffer.connect('changed', lambda buffer, book:
                       self.book.set('description', buffer.get_text(buffer.get_start_iter(),
                                     buffer.get_end_iter(), True)), self.book)
        self.window.connect('delete-event', self.quit)
        self.get('quit_button').connect('clicked', self.quit)
        self.get('about_button').connect('clicked', self.about)
        self.get('save_button').connect('clicked', self.save)
        self.get('warnings_button').connect('clicked', self.toggle_warnings)
        self.get('details_button').connect('clicked', self.toggle_details)
        self.get('calendar').connect('day-selected', self.edit_date)
        self.get('subject_entry').connect('activate', self.add_subject)
        self.get('remove_button').connect('clicked', self.remove_subject)
        self.get('cover_button').connect('button-press-event', self.add_or_set_cover)
        self.get('details_remove_button').connect('clicked', self.remove_element)
        self.get('popover_add_button').connect('clicked', self.add_element)
        self.get('popover_clear_button').connect('clicked', self.clear_popover)
        self.get('infobar').connect('response', lambda infobar, _response: infobar.destroy())
        self.get('details_add_button').connect('clicked', lambda _b:
                                               self.get('tag_entry').grab_focus())
        self.get('subjects').connect('cursor-changed', lambda view, button:
                                     button.set_sensitive((view.get_cursor().path is not None)),
                                     self.get('remove_button'))
        self.get('details').connect('cursor-changed', lambda view, button:
                                    button.set_sensitive((view.get_cursor().path is not None)),
                                    self.get('details_remove_button'))
        self.get('help_button').connect('clicked', lambda _b: Gtk.show_uri_on_window(self.window,
                                        f'{WEBSITE}/blob/main/gtk/README.md', Gdk.CURRENT_TIME))
        self.get('edit_button').connect('clicked', lambda _b: Gtk.show_uri_on_window(self.window,
                                        f'file://{self.book.opf}', Gdk.CURRENT_TIME))
        self.get('folder_button').connect('clicked', lambda _b: Gtk.show_uri_on_window(self.window,
                                          f'file://{self.book.tempdir.name}', Gdk.CURRENT_TIME))

        GLib.idle_add(self.volume_monitor_idle)
        GLib.idle_add(self.book_modified_idle)
        GLib.idle_add(self.opf_edited_idle)

        # Finalize window
        self.load_config()
        self.set_cover_image()
        self.update_widgets()
        self.window.show()


    # METHODS :


    def set_cover_image(self, path: str = None) -> None:
        if not path:
            path = self.book.get_cover()

        def scale_cover(file: str, rect: Gdk.Rectangle) -> GdkPixbuf.Pixbuf:
            return GdkPixbuf.Pixbuf.new_from_file_at_size(file, (rect.width * 0.3),
                                                          (rect.height * 0.9))

        if path and Path(path).exists():
            self.window.connect('size-allocate', lambda _win, allocation:
                                self.get('cover').set_from_pixbuf(scale_cover(path, allocation)))
        else:
            self.get('cover').set_from_icon_name('image-missing', Gtk.IconSize.DIALOG)

    def update_widgets(self) -> None:

        self.subjects.clear()
        self.details.clear()

        for field in ('title', 'creator', 'publisher', 'language'):
            try:
                self.get(field).set_text(self.book.get(field).text)
            except EPubError:
                ...

            self.get(field).connect('changed', self.add_or_set_field, field)

        # Date and calendar
        try:
            date = self.book.get('date').text
        except EPubError:
            date = time.strftime(TIME_FORMAT)

        my_time = None

        for format_string in (TIME_FORMAT, '%Y-%m-%d', '%Y'):
            try:
                my_time = time.strptime(date, format_string)
                break
            except ValueError:
                pass

        if my_time:  # GtkCalendar uses 0-11 for month
            self.get('calendar').select_month(int(my_time.tm_mon) - 1, my_time.tm_year)
            self.get('calendar').select_day(my_time.tm_mday)

            self.get('date').connect('changed', lambda entry:
                                     self.book.set('date', self.get('date').get_text()))

            try:
                icon_name = f'calendar-{my_time.tm_mday:02}'
            except AttributeError:
                icon_name = 'calendar'

            if Gtk.IconTheme.get_default().has_icon(icon_name):
                self.get('calendar_image').set_from_icon_name(icon_name, Gtk.IconSize.BUTTON)

        # Update liststores
        [self.subjects.append([sub.text]) for sub in self.book.get_all('subject')]

        for meta in self.book.metadata:
            if strip_namespace(meta.tag) != 'description':
                self.details.append([strip_namespace(meta.tag), meta.text,
                                    str(strip_namespaces(meta.attrib))])

    def load_config(self) -> None:
        if sys.platform == 'windows':
            self.config = Path(os.environ['%APPDATA%']) / 'epubmangler.conf'

        elif sys.platform == 'darwin':
            self.config = Path.home() / 'Library/Application Support/epubmangler/epubmangler.conf'

        else:  # linux or similar
            if 'XDG_CONFIG_HOME' in os.environ.keys():
                self.config = Path(os.environ['XDG_CONFIG_HOME']) / 'epubmangler.conf'

            elif Path(Path.home(), '.config').is_dir:
                self.config = Path.home() / '.config/epubmangler.conf'

            else:
                self.config = Path.home() / '.epubmangler.conf'

        if self.config.exists():
            with open(self.config, 'r') as config:
                self.warnings = json.load(config)['warnings']

        self.get('infobar').set_visible(self.warnings)
        self.get('warnings_button').set_property('active', not self.warnings)

    def save_config(self) -> None:
        if not self.config.parent.is_dir():
            os.mkdir(self.config.parent)

        with open(self.config, 'w') as config:
            json.dump({'warnings': self.warnings}, config, indent=4)


    # IDLE FUNCTIONS :


    def volume_monitor_idle(self) -> bool:
        button = self.get('device_button')

        # Look for connected AND mounted ebook readers
        for drive in Gio.VolumeMonitor.get().get_connected_drives():

            if drive.get_name() == 'Kindle Internal Storage':
                try:
                    mount = drive.get_volumes()[0].get_mount()
                except IndexError:  # Not mounted
                    button.hide()
                    break

                if mount:
                    root = Path(mount.get_root().get_path(), 'documents')

                    if Path(root).exists:
                        button.connect('clicked', self.send_book)
                        button.set_label('Send to Kindle')
                        button.show()
                else:
                    button.hide()

        return GLib.SOURCE_CONTINUE

    def book_modified_idle(self) -> bool:
        if self.book.modified:
            self.get('save_button').get_style_context().add_class('suggested-action')
            return GLib.SOURCE_REMOVE
        else:
            return GLib.SOURCE_CONTINUE

    def opf_edited_idle(self) -> bool:
        mtime = os.stat(self.book.opf).st_mtime

        if not self.mtime_cache:  # First run
            self.mtime_cache = mtime
        elif mtime != self.mtime_cache:
            self.mtime_cache = mtime
            self.book.parse_opf(modified=True)
            self.update_widgets()

        return GLib.SOURCE_CONTINUE


    # SIGNAL CALLBACKS :


    def about(self, _button: Gtk.ModelButton) -> None:
        dialog = Gtk.AboutDialog()
        dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_size(ICON, 64, 64))
        dialog.set_program_name('EPub Mangler')
        dialog.set_version(VERSION)
        dialog.set_copyright('Copyright © 2020-2021 David Keogh')
        dialog.set_license_type(Gtk.License.GPL_3_0)
        dialog.set_authors(['David Keogh <davidtkeogh@gmail.com>'])
        dialog.set_website(WEBSITE)
        dialog.set_transient_for(self.window)
        dialog.run()
        dialog.destroy()

    def add_element(self, _button: Gtk.Button) -> None:
        if self.get('tag_entry').get_text() and self.get('text_entry').get_text():

            try:  # Column 3 (attrib) is stored as a string
                attrib = json.loads(self.get('attrib_entry').get_text())
            except json.JSONDecodeError:
                attrib = {}

            element = Element(self.get('tag_entry').get_text())
            element.text = self.get('text_entry').get_text()
            element.attrib = attrib

            self.book.etree.find('./opf:metadata', NAMESPACES).append(element)
            self.details.append([self.get('tag_entry').get_text(),
                                self.get('text_entry').get_text(),
                                self.get('attrib_entry').get_text()])
            self.get('tag_entry').set_text('')
            self.get('text_entry').set_text('')
            self.get('attrib_entry').set_text('')
            self.get('popoveradd').popdown()

    def add_or_set_field(self, entry: Gtk.Entry, field: str) -> None:
        if self.book.has_element(field):
            self.book.set(field, entry.get_text())
        else:
            self.book.add(field, entry.get_text())

    def add_or_set_cover(self, _eb: Gtk.EventBox, _ev: Gdk.Event) -> None:
        dialog = Gtk.FileChooserDialog(title='Select an image', parent=self.window,
                                       action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        def update_preview(chooser: Gtk.FileChooserDialog, image: Gtk.Image) -> None:
            selected = chooser.get_preview_filename()

            if selected and mimetypes.guess_type(selected)[0] in IMAGE_TYPES:
                image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(selected, 256, 256))
                chooser.set_preview_widget_active(True)
            else:
                chooser.set_preview_widget_active(False)

        preview = Gtk.Image()
        dialog.set_preview_widget(preview)
        dialog.set_use_preview_label(False)
        dialog.connect('update-preview', update_preview, preview)

        img_filter = Gtk.FileFilter()
        img_filter.add_mime_type('image/*')
        img_filter.set_name('Image files')
        dialog.add_filter(img_filter)

        all_filter = Gtk.FileFilter()
        all_filter.add_pattern('*')
        all_filter.set_name('All files')
        dialog.add_filter(all_filter)

        if dialog.run() == Gtk.ResponseType.OK:
            filename = dialog.get_filename()

            if self.book.has_element('cover'):
                self.book.set_cover(filename)
            else:
                self.book.add_cover(filename)

            self.set_cover_image(filename)

        dialog.destroy()

    def add_subject(self, entry: Gtk.Entry) -> None:
        new_subject = entry.get_text()
        entry.set_text('')
        self.get('popoverentry').popdown()
        self.subjects.append([new_subject])
        self.book.add_subject(new_subject)

    def edit_date(self, calendar: Gtk.Calendar) -> None:
        date = calendar.get_date()
        month = date.month + 1  # GtkCalendar uses 0-11 for month
        icon_name = f'calendar-{date.day:02}'

        if Gtk.IconTheme.get_default().has_icon(icon_name):
            self.get('calendar_image').set_from_icon_name(icon_name, Gtk.IconSize.BUTTON)

        self.get('date').set_text(f'{date.year}-{month:02}-{date.day:02}')

    def cell_edited(self, _cr: Gtk.CellRendererText, path: str, new_text: str, col: int) -> None:
        self.details[path][col] = new_text

        try:
            attrib = self.details[path][2].replace("'", '"')
            attrib = json.loads(attrib)  # Column 3 (attrib) is stored as a string
        except json.JSONDecodeError:
            attrib = {}

        self.book.set(self.details[path][0], self.details[path][1], attrib)

    def clear_popover(self, _button: Gtk.Button) -> None:
        [entry.set_text('') for entry in (self.get('tag_entry'),
                                          self.get('text_entry'),
                                          self.get('attrib_entry'))]
    
    def quit(self, _caller: Gtk.Widget, _event: Gdk.Event = None) -> None:
        if self.book.modified and self.warnings:
            dialog = Gtk.MessageDialog(text='File has unsaved changes',
                                       message_type=Gtk.MessageType.QUESTION)
            dialog.format_secondary_text('Do you want to save them?')
            dialog.add_buttons(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE,
                               Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

            if dialog.run() == Gtk.ResponseType.OK:
                chooser = Gtk.FileChooserDialog(parent=self.window,
                                                action=Gtk.FileChooserAction.SAVE)
                chooser.set_current_name(Path(self.book.file).name)
                chooser.set_do_overwrite_confirmation(True)
                chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                    Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

                if chooser.run() == Gtk.ResponseType.OK:
                    self.book.save(chooser.get_filename())

                chooser.destroy()

            dialog.destroy()

        self.save_config()
        Gtk.main_quit()

    def remove_element(self, _button: Gtk.Button) -> None:
        iter = self.get('details').get_selection().get_selected()[1]

        if iter:
            try:  # Column 3 (attrib) is stored as a string
                attrib = json.loads(self.details.get_value(iter, 2))
            except json.JSONDecodeError:
                attrib = {}

            self.book.remove(self.details.get_value(iter, 0), attrib)
            self.details.remove(iter)

    def remove_subject(self, _button: Gtk.Button) -> None:
        iter = self.get('subjects').get_selection().get_selected()[1]

        if iter:
            self.book.remove_subject(self.subjects.get_value(iter, 0))
            self.subjects.remove(iter)

    def save(self, button: Gtk.Button) -> None:
        dialog = Gtk.FileChooserDialog(parent=self.window, action=Gtk.FileChooserAction.SAVE)
        dialog.set_current_name(Path(self.book.file).name)
        dialog.set_do_overwrite_confirmation(True)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

        box = Gtk.Box(spacing=12)
        box.set_hexpand(True)
        box.set_halign(Gtk.Align.END)
        type_label = Gtk.Label.new("EPub Version " + self.book.version)
        size_label = Gtk.Label.new(sizeof_format(self.book.file))
        size_label.set_halign(Gtk.Align.END)
        box.pack_start(type_label, False, False, 0)
        box.pack_start(size_label, False, True, 0)
        dialog.set_extra_widget(box)
        box.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            self.book.save(dialog.get_filename(), overwrite=True)
            self.book.modified = False
            button.get_style_context().remove_class('suggested-action')

        dialog.destroy()

    def send_book(self, _button: Gtk.Button, device_path: str) -> None:
        copy_to = Path(device_path, Path(self.book.file).name)

        if not Path(copy_to).exists:
            self.book.save(copy_to)
        else:
            dialog = Gtk.MessageDialog(text='File already exists',
                                       message_type=Gtk.MessageType.QUESTION)
            dialog.format_secondary_text(f'Replace file "{Path(self.book.file).name}"?')
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                               Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

            if dialog.run() == Gtk.ResponseType.OK:
                self.book.save(copy_to, overwrite=True)

            dialog.destroy()

    def toggle_details(self, button: Gtk.ToggleButton) -> None:
        self.update_widgets()
        self.get('details_form').set_visible(button.get_active())
        self.get('main_form').set_visible(not button.get_active())

    def toggle_warnings(self, button: Gtk.ModelButton) -> None:
        current = button.get_property('active')
        button.set_property('active', not current)
        self.warnings = current
        self.get('infobar').set_visible(current)


# Entry point
if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            # TODO: Delete
            # Select a random book from local collection of epubs
            folder = '/home/david/Projects/epubmangler/books/calibre'
            filename = Path(folder, random.choice(os.listdir(folder)))
        else:
            filename = Path(sys.argv[1])
        if not filename.is_file():
            raise SystemExit(f'Usage: {sys.argv[0]} [FILE]')
    else:
        raise SystemExit(f'Usage: {sys.argv[0]} [FILE]')

    app = Application(filename)
    Gtk.main()
