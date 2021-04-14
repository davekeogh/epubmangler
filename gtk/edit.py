#!/usr/bin/env python
"""A GTK interface to the epubmangler library."""

# TODO:
# - Use Gtk.Application, Gtk.ApplicationWindow

import mimetypes, os, os.path, random, subprocess, sys

from epubmangler import EPub, IMAGE_TYPES, is_epub, strip_namespace, strip_namespaces, VERSION

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, GdkPixbuf, Gio, Gtk

# TODO: Delete
# This stuff needs to get set during install
BUILDER = '/home/david/Projects/epubmangler/gtk/widgets.xml'
FOLDER = '/home/david/Projects/epubmangler/books/calibre'
ICON = '/home/david/Projects/epubmangler/gtk/icon.svg'


def scale_cover(file: str, allocation: Gdk.Rectangle) -> GdkPixbuf.Pixbuf:
    height = allocation.height
    width = allocation.width / 3
    return GdkPixbuf.Pixbuf.new_from_file_at_scale(file, width, height, True)


# Signal callbacks
def about(_b: Gtk.ModelButton, window: Gtk.Window) -> None:
    dialog = Gtk.AboutDialog()
    dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_size(ICON, 64, 64))
    dialog.set_program_name('EPub Mangler')
    dialog.set_version(VERSION)
    dialog.set_copyright('Copyright © 2020-2021 David Keogh')
    dialog.set_license_type(Gtk.License.GPL_3_0)
    dialog.set_authors(['David Keogh <davidtkeogh@gmail.com>'])
    dialog.set_website('https://github.com/davekeogh/epubmangler')
    dialog.set_transient_for(window)

    if dialog.run() == Gtk.ResponseType.DELETE_EVENT:
        dialog.destroy()


def add_element(_b: Gtk.Button, model: Gtk.ListStore, view: Gtk.TreeView, book: EPub) -> None:
    ...


def remove_element(_b: Gtk.Button, model: Gtk.ListStore, view: Gtk.TreeView, book: EPub) -> None:
    iter = view.get_selection().get_selected()[1]

    if iter:
        book.remove(model.get_value(iter, 0), model.get_value(iter, 2))
        model.remove(iter)


def send_book(_b: Gtk.Button, book: EPub, device_path: str) -> None:
    file_name = os.path.basename(book.file)
    copy_to = os.path.join(device_path, file_name)

    if not os.path.exists(copy_to):
        book.save(copy_to)

    else:
        dialog = Gtk.MessageDialog(text='File already exists',
                                   message_type=Gtk.MessageType.QUESTION)
        dialog.format_secondary_text(f'Replace file "{file_name}"?')
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

        if dialog.run() == Gtk.ResponseType.OK:
            book.save(copy_to, overwrite=True)

        dialog.destroy()


def cell_edited(_c: Gtk.CellRendererText,
                path: str, new_text: str, model: Gtk.ListStore, col: int) -> None:
    model[path][col] = new_text


def save_file(_b: Gtk.Button, book: EPub, window: Gtk.Window) -> None:
    dialog = Gtk.FileChooserDialog(parent=window, action=Gtk.FileChooserAction.SAVE)
    dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                       Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

    if dialog.run() == Gtk.ResponseType.OK:
        filename = dialog.get_filename()

        if not os.path.exists(filename):
            book.save(filename)

    dialog.destroy()


def details_toggle(button: Gtk.ToggleButton,
                   cover: Gtk.Button, main: Gtk.Grid, details: Gtk.TreeView) -> None:
    details_on = button.get_active()
    details.set_visible(details_on)
    main.set_visible(not details_on)
    cover.set_visible(not details_on)


def set_cover(_b: Gtk.Button, image: Gtk.Image, content_area: Gtk.Box, book: EPub) -> None:
    dialog = Gtk.FileChooserDialog(title='Select an image', parent=window,
                                   action=Gtk.FileChooserAction.OPEN)
    dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                       Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

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

        if mimetypes.guess_type(filename)[0] in IMAGE_TYPES:
            image.set_from_pixbuf(scale_cover(filename, content_area.get_allocation()))
            book.set_cover(filename)

    dialog.destroy()


def edit_date(calendar: Gtk.Calendar, entry: Gtk.Entry) -> None:
    date = calendar.get_date()
    entry.set_text(f'{date.year}-{date.month:02}-{date.day:02}')


def add_subject(entry: Gtk.Entry, model: Gtk.ListStore, po: Gtk.Popover, book: EPub) -> None:
    new_subject = entry.get_text()

    model.append([new_subject])
    book.add_subject(new_subject)

    entry.set_text('')
    po.popdown()


def remove_subject(_b: Gtk.Button, model: Gtk.ListStore, view: Gtk.TreeView, book: EPub) -> None:
    iter = view.get_selection().get_selected()[1]

    if iter:
        book.remove_subject(model.get_value(iter, 0))
        model.remove(iter)


# Entry point
if __name__ == '__main__':
    if len(sys.argv) > 1:
        if is_epub(sys.argv[1]):
            book = EPub(sys.argv[1])
        elif sys.argv[1] == 'test':
            # TODO: Delete
            # Select a random book from local collection of epubs
            books = os.listdir(FOLDER)
            book = EPub(os.path.join(FOLDER, random.choice(books)))
    else:
        book = None

    builder = Gtk.Builder()
    builder.add_from_file(BUILDER)

    # Widgets
    window = builder.get_object('window')
    title_label = builder.get_object('title_label')
    device_button = builder.get_object('device_button')
    save_button = builder.get_object('save_button')
    details_button = builder.get_object('details_button')
    open_button = builder.get_object('open_button')
    menu_button = builder.get_object('menu_button')
    content_area = builder.get_object('box')
    main_area = builder.get_object('main')
    cover = builder.get_object('cover')
    cover_button = builder.get_object('cover_button')
    calendar = builder.get_object('calendar')
    date_entry = builder.get_object('date')
    subject_view = builder.get_object('subjects')
    subject_entry = builder.get_object('subject_entry')
    remove_button = builder.get_object('remove_button')
    description = builder.get_object('description')
    details = builder.get_object('details')
    details_area = builder.get_object('details_area')
    add_element_button = builder.get_object('details_add_button')
    remove_element_button = builder.get_object('details_remove_button')
    edit_button = builder.get_object('details_edit_button')
    infobar = builder.get_object('infobar')
    popover_cal = builder.get_object('popovercalendar')
    popover_entry = builder.get_object('popoverentry')
    about_button = builder.get_object('about_button')
    quit_button = builder.get_object('quit_button')

    list_model = Gtk.ListStore(str)
    details_model = Gtk.ListStore(str, str, str)
    volume_monitor = Gio.VolumeMonitor.get()

    # Signals
    window.connect('destroy', Gtk.main_quit)
    save_button.connect('clicked', save_file, book, window)
    details_button.connect('toggled', details_toggle, cover_button, main_area, details_area)
    calendar.connect('day-selected', edit_date, date_entry)
    subject_entry.connect('activate', add_subject, list_model, popover_entry, book)
    remove_button.connect('clicked', remove_subject, list_model, subject_view, book)
    cover_button.connect('clicked', set_cover, cover, content_area, book)
    add_element_button.connect('clicked', add_element, details_model, details, book)
    remove_element_button.connect('clicked', remove_element, details_model, details, book)
    infobar.connect('response', lambda infobar, _response: infobar.destroy())
    date_entry.connect('icon-press', lambda _entry, _icon, _event, po: po.popup(), popover_cal)
    edit_button.connect('clicked', lambda _b, book: subprocess.run(['xdg-open', book.opf]), book)
    about_button.connect('clicked', about, window)
    quit_button.connect('clicked', Gtk.main_quit)

    if book:
        title_label.set_text(os.path.basename(book.file))
        window.set_title(os.path.basename(book.file))

        # Look for connected AND mounted ebook readers
        for drive in volume_monitor.get_connected_drives():
            if drive.get_name() == 'Kindle Internal Storage':
                mount = drive.get_volumes()[0].get_mount()

                if mount:
                    root = os.path.join(mount.get_root().get_path(), 'documents')

                    if os.path.exists(root):
                        device_button.connect('clicked', send_book, book, root)
                        device_button.set_label('Send to Kindle')
                        device_button.show()

        # Populate fields
        for field in ('title', 'creator', 'date', 'publisher', 'language'):
            try:
                builder.get_object(field).set_text(book.get(field).text)
            except NameError:
                pass

            builder.get_object(field).connect('changed',
                                              lambda entry, book, field:
                                              book.set(field, entry.get_text()),
                                              book, field)

        for subject in book.get_all('subject'):
            list_model.append([subject.text])

        subject_view.set_model(list_model)
        subject_view.append_column(Gtk.TreeViewColumn('Subjects', Gtk.CellRendererText(), text=0))

        # Description
        try:
            description_text = book.get('description').text
        except NameError:
            description_text = None

        if description_text:
            buffer = Gtk.TextBuffer()
            buffer.set_text(description_text)

            buffer.connect('changed',
                           lambda buffer, book:
                           book.set('description', buffer.get_text(buffer.get_start_iter(),
                                                                   buffer.get_end_iter(), True)),
                           book)

            description.set_buffer(buffer)

        # Details view
        for meta in book.metadata():
            if strip_namespace(meta.tag) != 'description':
                details_model.append([strip_namespace(meta.tag), meta.text,
                                     str(strip_namespaces(meta.attrib))])
        details.set_model(details_model)

        cell = Gtk.CellRendererText()
        cell.set_property('editable', True)
        cell.connect('edited', cell_edited, details_model, 0)

        column = Gtk.TreeViewColumn('Element', cell, text=0)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        details.append_column(column)

        cell = Gtk.CellRendererText()
        cell.set_property('editable', True)
        cell.connect('edited', cell_edited, details_model, 1)

        column = Gtk.TreeViewColumn('Text', cell, text=1)
        column.set_min_width(details.get_allocation().width * 0.6)
        column.set_expand(True)
        details.append_column(column)

        cell = Gtk.CellRendererText()
        cell.set_property('editable', True)
        cell.connect('edited', cell_edited, details_model, 2)

        column = Gtk.TreeViewColumn('Attributes', cell, text=2)
        column.set_expand(True)
        details.append_column(column)

        # The window needs to be shown first, so that the cover can be scaled to fit.
        window.show()

        if book.get_cover():
            cover.set_from_pixbuf(scale_cover(book.get_cover(), content_area.get_allocation()))
        else:
            cover.set_from_icon_name('image-missing', Gtk.IconSize.DIALOG)

    else:
        content_area.hide()
        details_button.hide()
        save_button.hide()
        device_button.hide()
        open_button.show()
        window.show()

    Gtk.main()
