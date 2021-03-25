#!/usr/bin/env python
"""A GTK interface to the epubmangler library."""

import os, os.path, random, sys

from epubmangler import EPub, is_epub

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, GdkPixbuf, Gtk, GLib

# We use webkit to render the description text if it's available
try:
    gi.require_version('WebKit2', '4.0')
    from gi.repository import WebKit2
except ValueError:
    WebKit2 = None


def scale_cover(file: str, allocation: Gdk.Rectangle) -> GdkPixbuf.Pixbuf:
    height = allocation.height 
    width = allocation.width / 3
    return GdkPixbuf.Pixbuf.new_from_file_at_scale(file, width, height, True)

def set_cover(button: Gtk.Button) -> None:
    pass

def edit_date(calendar: Gtk.Calendar, entry: Gtk.Entry):
    pass

def add_subject(entry: Gtk.Entry, model: Gtk.ListStore, popover: Gtk.Popover) -> None:
    model.append([entry.get_text()])
    entry.set_text('')
    popover.popdown()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if is_epub(sys.argv[1]):
            book = EPub(sys.argv[1])
        elif sys.argv[1] == 'test':
            # TODO: Delete
            # Select a random book from local collection of epubs
            folder = 'calibre'
            # folder = 'gutenberg'
            books = os.listdir(folder)
            book = EPub(os.path.join(folder, random.choice(books)))
    else:
        book = None
    
    # TODO: Delete
    if book:
        print(book.file)
    
    builder = Gtk.Builder()
    builder.add_from_file('window.xml')
    
    # Widgets
    window = builder.get_object('window')
    title_label = builder.get_object('title_label')
    content_area = builder.get_object('box')
    cover = builder.get_object('cover')
    cover_button = builder.get_object('cover_button')
    calendar = builder.get_object('calendar')
    date_entry = builder.get_object('date')
    subject_view = builder.get_object('subjects')
    subject_entry = builder.get_object('subject_entry')
    description = builder.get_object('description') # Replaced by WebKit2.WebView 

    list_model = Gtk.ListStore(str)

    # Signals 
    window.connect('destroy', Gtk.main_quit)
    calendar.connect('day-selected', edit_date, date_entry)
    date_entry.connect('icon-press', lambda _entry, _icon, _event, popover: popover.popup(), builder.get_object('popovercalendar'))
    subject_entry.connect('activate', add_subject, list_model, builder.get_object('popoverentry'))
    cover_button.connect('activate', set_cover)

    if book:
        builder.get_object('headerbar').show_all()
        title_label.set_text(os.path.basename(book.file))
        window.set_title(os.path.basename(book.file))
        
        for field in ('title', 'creator', 'date', 'publisher', 'language'):
            try:
                builder.get_object(field).set_text(book.get(field).text)
            except NameError:
                pass
        
        for subject in book.get_all('subject'):
            list_model.append([subject.text])
        subject_view.set_model(list_model)
        subject_view.append_column(Gtk.TreeViewColumn('Subjects', Gtk.CellRendererText(), text=0))

        try:
            description_text = book.get('description').text
        except NameError:
            description_text = None

        if WebKit2 and description_text:
            description.destroy()
            
            # TODO: Create a style sheet based on the current gtk style
            cm = WebKit2.UserContentManager()
            css = 'body { background-color: black; text-align: center; color: white;}'
            cm.add_style_sheet(WebKit2.UserStyleSheet(css, 0, 0, None, None))
            
            description = WebKit2.WebView.new_with_user_content_manager(cm)
            description.set_vexpand(True)
            description.load_bytes(GLib.Bytes(description_text.encode('utf-8')))
            builder.get_object('description_window').add(description)
            description.show()

        elif description_text:
            buffer = Gtk.TextBuffer()
            buffer.set_text(description_text)
            description.set_buffer(buffer)

        window.show()
        # The window needs to be shown before the cover so that it can be scaled to fit
        cover.set_from_pixbuf(scale_cover(book.get_cover(), content_area.get_allocation()))
    
    else:
        content_area.hide()
        window.show()
    

    Gtk.main()
