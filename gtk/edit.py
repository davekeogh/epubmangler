#!/usr/bin/env python
"""A GTK interface to the epubmangler library."""

# TODO:
# - Use Gtk.Application, Gtk.ApplicationWindow

import mimetypes, os, os.path, random, sys, time

from epubmangler import (
    EPub,
    IMAGE_TYPES, VERSION, TIME_FORMAT, WEBSITE, XPATHS,
    is_epub, strip_namespace, strip_namespaces
)

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk

# TODO: This needs to get set during install
RESOURCE_DIR = '/home/david/Projects/epubmangler/gtk'
BUILDER = os.path.join(RESOURCE_DIR, 'widgets.xml')
ICON = os.path.join(RESOURCE_DIR, 'epubmangler.svg')


def scale_cover(file: str, allocation: Gdk.Rectangle) -> GdkPixbuf.Pixbuf:
    height = allocation.height * 0.9
    width = allocation.width * 0.3

    return GdkPixbuf.Pixbuf.new_from_file_at_size(file, width, height)


def volume_monitor_idle(book: EPub, button: Gtk.Button) -> bool:
    # Look for connected AND mounted ebook readers
    for drive in Gio.VolumeMonitor.get().get_connected_drives():
        if drive.get_name() == 'Kindle Internal Storage':
            try:
                mount = drive.get_volumes()[0].get_mount()
            except IndexError:  # Not mounted
                button.hide()
                break

            if mount:
                root = os.path.join(mount.get_root().get_path(), 'documents')

                if os.path.exists(root):
                    button.connect('clicked', send_book, book, root)
                    button.set_label('Send to Kindle')
                    button.show()

            else:
                button.hide()

    return GLib.SOURCE_CONTINUE


def file_modified_idle(book: EPub, button: Gtk.Button) -> bool:
    if book.modified:
        button.get_style_context().add_class('suggested-action')

        return GLib.SOURCE_REMOVE
    else:
        return GLib.SOURCE_CONTINUE


def sync_fields(book: EPub, builder: Gtk.Builder, subjects: Gtk.ListStore,
                details: Gtk.ListStore) -> None:

    subjects.clear()
    details.clear()

    for field in ('title', 'creator', 'publisher', 'language'):
        try:
            builder.get_object(field).set_text(book.get(field).text)
        except NameError:
            pass

    try:
        date = book.get('date').text
    except NameError:
        date = time.strftime(TIME_FORMAT)
    builder.get_object('date').set_text(date.split('T')[0])

    [subjects.append([subject.text]) for subject in book.get_all('subject')]

    for meta in book.metadata:
        if strip_namespace(meta.tag) != 'description':
            details.append([strip_namespace(meta.tag), meta.text,
                           str(strip_namespaces(meta.attrib))])


# Signal callbacks:

def quit_confirm_unsaved(_caller: Gtk.Widget, window: Gtk.Window, book: EPub) -> None:
    if book.modified:
        dialog = Gtk.MessageDialog(text='File has unsaved changes',
                                   message_type=Gtk.MessageType.QUESTION)
        dialog.format_secondary_text('Do you want to save them?')
        dialog.add_buttons(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE,
                           Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

        if dialog.run() == Gtk.ResponseType.OK:
            chooser = Gtk.FileChooserDialog(parent=window, action=Gtk.FileChooserAction.SAVE)
            chooser.set_current_name(os.path.basename(book.file))
            chooser.set_do_overwrite_confirmation(True)
            chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

            if chooser.run() == Gtk.ResponseType.OK:
                book.save(chooser.get_filename())

            chooser.destroy()

        dialog.destroy()

    Gtk.main_quit()


def about(_b: Gtk.ModelButton, window: Gtk.Window) -> None:
    dialog = Gtk.AboutDialog()
    dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_size(ICON, 64, 64))
    dialog.set_program_name('EPub Mangler')
    dialog.set_version(VERSION)
    dialog.set_copyright('Copyright © 2020-2021 David Keogh')
    dialog.set_license_type(Gtk.License.GPL_3_0)
    dialog.set_authors(['David Keogh <davidtkeogh@gmail.com>'])
    dialog.set_website(WEBSITE)
    dialog.set_transient_for(window)

    dialog.run()
    dialog.destroy()


def add_element(_b: Gtk.Button, popover: Gtk.Popover, model: Gtk.ListStore, book: EPub,
                tag_entry: Gtk.Entry, text_entry: Gtk.Entry, attrib_entry: Gtk.Entry) -> None:
    if tag_entry.get_text() and text_entry.get_text():
        if not attrib_entry.get_text() or type(eval(attrib_entry.get_text())) != dict:
            attrib_entry.set_text('{}')

        book.add(tag_entry.get_text(), text_entry.get_text(), eval(attrib_entry.get_text()))
        model.append([tag_entry.get_text(), text_entry.get_text(), attrib_entry.get_text()])
        tag_entry.set_text('')
        text_entry.set_text('')
        attrib_entry.set_text('')
        popover.popdown()


def remove_element(_b: Gtk.Button, model: Gtk.ListStore, view: Gtk.TreeView, book: EPub) -> None:
    iter = view.get_selection().get_selected()[1]

    if iter:
        book.remove(model.get_value(iter, 0), model.get_value(iter, 2))
        model.remove(iter)


def send_book(_b: Gtk.Button, book: EPub, device_path: str) -> None:
    copy_to = os.path.join(device_path, os.path.basename(book.file))

    if not os.path.exists(copy_to):
        book.save(copy_to)

    else:
        dialog = Gtk.MessageDialog(text='File already exists',
                                   message_type=Gtk.MessageType.QUESTION)
        dialog.format_secondary_text(f'Replace file "{os.path.basename(book.file)}"?')
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

        if dialog.run() == Gtk.ResponseType.OK:
            book.save(copy_to, overwrite=True)

        dialog.destroy()


def cell_edited(_c: Gtk.CellRendererText,
                path: str, new_text: str, model: Gtk.ListStore, col: int, book: EPub) -> None:
    model[path][col] = new_text
    # column 3 (attrib) is a dict stored as a string in the liststore
    book.set(model[path][0], model[path][1], eval(model[path][2]))


def save_file(_b: Gtk.Button, book: EPub, window: Gtk.Window) -> None:
    dialog = Gtk.FileChooserDialog(parent=window, action=Gtk.FileChooserAction.SAVE)
    dialog.set_current_name(os.path.basename(book.file))
    dialog.set_do_overwrite_confirmation(True)
    dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                       Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

    if dialog.run() == Gtk.ResponseType.OK:
        book.save(dialog.get_filename())

    dialog.destroy()


def details_toggle(button: Gtk.ToggleButton, builder: Gtk.Builder, subjects: Gtk.ListStore,
                   details: Gtk.ListStore, book: EPub) -> None:
    sync_fields(book, builder, subjects, details)
    builder.get_object('details_area').set_visible(button.get_active())
    builder.get_object('main').set_visible(not button.get_active())
    builder.get_object('cover').set_visible(not button.get_active())


def update_preview(chooser: Gtk.FileChooserDialog, image: Gtk.Image) -> None:
    selected = chooser.get_preview_filename()

    if selected and mimetypes.guess_type(selected)[0] in IMAGE_TYPES:
        image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(selected, 256, 256))
        chooser.set_preview_widget_active(True)
    else:
        chooser.set_preview_widget_active(False)


def set_cover(_eb: Gtk.EventBox, _ev: Gdk.Event,
              image: Gtk.Image, window: Gtk.Window, book: EPub) -> None:
    dialog = Gtk.FileChooserDialog(title='Select an image', parent=window,
                                   action=Gtk.FileChooserAction.OPEN)
    dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                       Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

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

        if mimetypes.guess_type(filename)[0] in IMAGE_TYPES:
            image.set_from_pixbuf(scale_cover(filename, window.get_allocation()))
            book.set_cover(filename)

    dialog.destroy()


def edit_date(calendar: Gtk.Calendar, entry: Gtk.Entry, icon: Gtk.Image) -> None:
    date = calendar.get_date()
    month = date.month + 1  # GtkCalendar uses 0-11 for month
    entry.set_text(f'{date.year}-{month:02}-{date.day:02}')

    icon_name = f'calendar-{date.day:02}'

    if Gtk.IconTheme.get_default().has_icon(icon_name):
        icon.set_from_icon_name(icon_name, Gtk.IconSize.BUTTON)


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
            folder = '/home/david/Projects/epubmangler/books/calibre'
            books = os.listdir(folder)
            book = EPub(os.path.join(folder, random.choice(books)))
        else:
            raise SystemExit(f'Usage: {sys.argv[0]} [FILE]')
    else:
        raise SystemExit(f'Usage: {sys.argv[0]} [FILE]')

    # Widgets
    builder = Gtk.Builder.new_from_file(BUILDER)
    window = builder.get_object('window')
    title_label = builder.get_object('title_label')
    device_button = builder.get_object('device_button')
    save_button = builder.get_object('save_button')
    details_button = builder.get_object('details_button')
    menu_button = builder.get_object('menu_button')
    cover = builder.get_object('cover')
    cover_button = builder.get_object('cover_button')
    calendar = builder.get_object('calendar')
    date_entry = builder.get_object('date')
    subject_view = builder.get_object('subjects')
    subject_entry = builder.get_object('subject_entry')
    remove_button = builder.get_object('remove_button')
    calendar_image = builder.get_object('calendar_image')
    description = builder.get_object('description')
    details = builder.get_object('details')
    add_element_button = builder.get_object('details_add_button')
    remove_element_button = builder.get_object('details_remove_button')
    edit_button = builder.get_object('details_edit_button')
    fm_button = builder.get_object('folder_button')
    infobar = builder.get_object('infobar')
    popover_cal = builder.get_object('popovercalendar')
    popover_entry = builder.get_object('popoverentry')
    help_button = builder.get_object('help_button')
    about_button = builder.get_object('about_button')
    quit_button = builder.get_object('quit_button')
    tag_entry = builder.get_object('tag_entry')
    text_entry = builder.get_object('text_entry')
    attrib_entry = builder.get_object('attrib_entry')
    popover_add = builder.get_object('popoveradd')
    popover_add_button = builder.get_object('popover_add_button')
    popover_clear_button = builder.get_object('popover_clear_button')

    subjects_model = Gtk.ListStore(str)
    details_model = Gtk.ListStore(str, str, str)
    tag_model = Gtk.ListStore(str)

    GLib.idle_add(volume_monitor_idle, book, device_button)
    GLib.idle_add(file_modified_idle, book, save_button)

    # Signal connection
    window.connect('destroy', quit_confirm_unsaved, window, book)
    quit_button.connect('clicked', quit_confirm_unsaved, window, book)
    about_button.connect('clicked', about, window)
    save_button.connect('clicked', save_file, book, window)
    details_button.connect('toggled', details_toggle, builder, subjects_model, details_model, book)
    calendar.connect('day-selected', edit_date, date_entry, calendar_image)
    subject_entry.connect('activate', add_subject, subjects_model, popover_entry, book)
    remove_button.connect('clicked', remove_subject, subjects_model, subject_view, book)
    cover_button.connect('button-press-event', set_cover, cover, window, book)
    remove_element_button.connect('clicked', remove_element, details_model, details, book)
    popover_add_button.connect('clicked', add_element, popover_add, details_model, book,
                               tag_entry, text_entry, attrib_entry)
    infobar.connect('response', lambda infobar, _response: infobar.destroy())
    date_entry.connect('icon-press', lambda _entry, _icon, _event, po: po.popup(), popover_cal)
    add_element_button.connect('clicked', lambda _b, entry: entry.grab_focus(), tag_entry)
    popover_clear_button.connect('clicked', lambda _b, tag, text, attrib:
                                 [entry.set_text('') for entry in (tag, text, attrib)],
                                 tag_entry, text_entry, attrib_entry)
    subject_view.connect('cursor-changed', lambda view, button:
                         button.set_sensitive((view.get_cursor().path is not None)), remove_button)
    details.connect('cursor-changed', lambda view, button:
                    button.set_sensitive((view.get_cursor().path is not None)),
                    remove_element_button)
    help_button.connect('clicked', lambda _b:
                        Gtk.show_uri_on_window(window, f'{WEBSITE}/blob/main/gtk/README.md',
                                               Gdk.CURRENT_TIME))
    edit_button.connect('clicked', lambda _b:
                        Gtk.show_uri_on_window(window, f'file://{book.opf}', Gdk.CURRENT_TIME))
    fm_button.connect('clicked', lambda _b:
                      Gtk.show_uri_on_window(window, f'file://{book.tempdir.name}',
                                             Gdk.CURRENT_TIME))

    # Cover image
    if book.get_cover() and os.path.exists(book.get_cover()):
        window.connect('size-allocate', lambda _win, allocation:
                       cover.set_from_pixbuf(scale_cover(book.get_cover(), allocation)))
    else:
        cover.set_from_icon_name('image-missing', Gtk.IconSize.DIALOG)

    # Complete tags from the XPATHS dict
    for key in XPATHS.keys():
        tag_model.append([key])

    tag_completion = Gtk.EntryCompletion()
    tag_completion.set_model(tag_model)
    tag_completion.set_text_column(0)
    tag_entry.set_completion(tag_completion)

    # Populate fields
    for field in ('title', 'creator', 'publisher', 'language'):
        try:
            builder.get_object(field).set_text(book.get(field).text)
        except NameError:
            pass

        builder.get_object(field).connect('changed', lambda entry, book, field:
                                          book.set(field, entry.get_text()),
                                          book, field)

    # Date and calendar
    try:
        date = book.get('date').text
    except NameError:
        date = time.strftime(TIME_FORMAT)

    my_time = None

    for format_string in (TIME_FORMAT, '%Y-%m-%d', '%Y'):
        try:
            my_time = time.strptime(date, format_string)
            break
        except ValueError:
            pass

    if my_time:
        # GtkCalendar uses 0-11 for month
        calendar.select_month(int(my_time.tm_mon) - 1, my_time.tm_year)
        calendar.select_day(my_time.tm_mday)

    builder.get_object('date').set_text(date.split('T')[0])  # Hide the useless time information

    builder.get_object('date').connect('changed', lambda entry, book:
                                       book.set('date', entry.get_text()),
                                       book)

    # Subject tags
    [subjects_model.append([subject.text]) for subject in book.get_all('subject')]
    subject_view.set_model(subjects_model)
    subject_view.append_column(Gtk.TreeViewColumn('Subjects', Gtk.CellRendererText(), text=0))

    # Description
    try:
        description_text = book.get('description').text
    except NameError:
        description_text = None

    if description_text:
        buffer = Gtk.TextBuffer()
        buffer.set_text(description_text)

        buffer.connect('changed', lambda buffer, book:
                       book.set('description', buffer.get_text(buffer.get_start_iter(),
                                                               buffer.get_end_iter(), True)),
                       book)

        description.set_buffer(buffer)

    # Details view
    for meta in book.metadata:
        if strip_namespace(meta.tag) != 'description':
            details_model.append([strip_namespace(meta.tag), meta.text,
                                 str(strip_namespaces(meta.attrib))])

    details.set_model(details_model)

    cell = Gtk.CellRendererText()
    cell.set_property('editable', True)
    cell.connect('edited', cell_edited, details_model, 0, book)

    column = Gtk.TreeViewColumn('Tag', cell, text=0)
    column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
    details.append_column(column)

    cell = Gtk.CellRendererText()
    cell.set_property('editable', True)
    cell.connect('edited', cell_edited, details_model, 1, book)

    column = Gtk.TreeViewColumn('Text', cell, text=1)
    column.set_min_width(details.get_allocation().width * 0.6)
    column.set_expand(True)
    details.append_column(column)

    cell = Gtk.CellRendererText()
    cell.set_property('editable', True)
    cell.connect('edited', cell_edited, details_model, 2, book)

    column = Gtk.TreeViewColumn('Attributes', cell, text=2)
    column.set_expand(True)
    details.append_column(column)

    # Window
    title_label.set_text(os.path.basename(book.file))
    window.set_title(os.path.basename(book.file))
    window.set_icon_from_file(ICON)
    window.show()

    Gtk.main()
