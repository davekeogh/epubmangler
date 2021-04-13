#!/usr/bin/env python
"""A GTK interface to the epubmangler library."""

# TODO:
# - look into using libhandy widgets, they will be added to Gtk 4 with libadwaita
# - Use Gtk.Application, Gtk.ApplicationWindow

import mimetypes, os, os.path, random, sys

from epubmangler import EPub, IMAGE_TYPES, is_epub, strip_namespace, strip_namespaces

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, GdkPixbuf, Gio, Gtk


def send_book(button: Gtk.Button, book: EPub, device_path: str, window: Gtk.Window) -> None:
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


def scale_cover(file: str, allocation: Gdk.Rectangle) -> GdkPixbuf.Pixbuf:
    height = allocation.height
    width = allocation.width / 3
    return GdkPixbuf.Pixbuf.new_from_file_at_scale(file, width, height, True)


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

    all_filter = Gtk.FileFilter()
    all_filter.add_pattern('*')
    all_filter.set_name('All files')

    dialog.add_filter(img_filter)
    dialog.add_filter(all_filter)

    if dialog.run() == Gtk.ResponseType.OK:
        filename = dialog.get_filename()

        if mimetypes.guess_type(filename)[0] in IMAGE_TYPES:
            image.set_from_pixbuf(scale_cover(filename, content_area.get_allocation()))
            book.set_cover(filename)

    dialog.destroy()


def edit_date(calendar: Gtk.Calendar, entry: Gtk.Entry, popover: Gtk.Popover) -> None:
    date = calendar.get_date()
    entry.set_text(f'{date.year}-{date.month:02}-{date.day:02}')


def add_subject(entry: Gtk.Entry, model: Gtk.ListStore, po: Gtk.Popover, book: EPub) -> None:
    new_subject = entry.get_text()

    model.append([new_subject])
    book.add_subject(new_subject)

    entry.set_text('')
    po.popdown()


def remove_subject(_b: Gtk.Button, model: Gtk.ListStore, view: Gtk.TreeView, book: EPub) -> None:
    selection = view.get_selection().get_selected()[1]
    subject = model.get_value(selection, 0)

    if selection:
        model.remove(selection)
        book.remove_subject(subject)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if is_epub(sys.argv[1]):
            book = EPub(sys.argv[1])
        elif sys.argv[1] == 'test':
            # TODO: Delete
            # Select a random book from local collection of epubs
            folder = 'books/calibre'
            # folder = 'books/gutenberg'
            books = os.listdir(folder)
            book = EPub(os.path.join(folder, random.choice(books)))
    else:
        book = None

    builder = Gtk.Builder()
    builder.add_from_file('window.xml')

    # Widgets
    window = builder.get_object('window')
    title_label = builder.get_object('title_label')
    device_button = builder.get_object('device_button')
    save_button = builder.get_object('save_button')
    details_button = builder.get_object('details_button')
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
    description = builder.get_object('description')  # Replaced by WebKit2.WebView
    details = builder.get_object('details')
    details_window = builder.get_object('details_window')

    popover_cal = builder.get_object('popovercalendar')
    popover_entry = builder.get_object('popoverentry')

    list_model = Gtk.ListStore(str)
    details_model = Gtk.ListStore(str, str, str)

    volume_monitor = Gio.VolumeMonitor.get()

    for drive in volume_monitor.get_connected_drives():
        if drive.get_name() == 'Kindle Internal Storage':
            mount = drive.get_volumes()[0].get_mount()

            if mount:
                root = os.path.join(mount.get_root().get_path(), 'documents')

                if os.path.exists(root):
                    device_button.connect('clicked', send_book, book, root, window)
                    device_button.set_label('Send to Kindle')
                    device_button.show()

    # Signals
    window.connect('destroy', Gtk.main_quit)
    save_button.connect('clicked', save_file, book, window)
    details_button.connect('toggled', details_toggle, cover_button, main_area, details_window)
    calendar.connect('day-selected', edit_date, date_entry, popover_cal)
    date_entry.connect('icon-press', lambda _entry, _icon, _event, po: po.popup(), popover_cal)
    subject_entry.connect('activate', add_subject, list_model, popover_entry, book)
    remove_button.connect('clicked', remove_subject, list_model, subject_view, book)
    cover_button.connect('clicked', set_cover, cover, content_area, book)

    if book:
        save_button.show()
        title_label.set_text(os.path.basename(book.file))
        window.set_title(os.path.basename(book.file))

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

        for meta in book.metadata():
            if strip_namespace(meta.tag) != 'description':
                details_model.append([strip_namespace(meta.tag), meta.text,
                                     str(strip_namespaces(meta.attrib))])
        details.set_model(details_model)

        cell = Gtk.CellRendererText()
        cell.set_property('editable', True)
        cell.connect('edited', cell_edited, details_model, 0)

        column = Gtk.TreeViewColumn('Tag', cell, text=0)
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

        column = Gtk.TreeViewColumn('Attrib', cell, text=2)
        column.set_expand(True)
        details.append_column(column)

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

        window.show()
        # The window needs to be shown before the cover so that it can be scaled to fit
        image_path = book.get_cover()

        if image_path:
            cover.set_from_pixbuf(scale_cover(image_path, content_area.get_allocation()))
        else:
            cover.set_from_icon_name('image-missing', Gtk.IconSize.DIALOG)

    else:
        content_area.hide()
        window.show()

    Gtk.main()
