#!/usr/bin/env python
"""A GTK interface to the epubmangler library."""

import os, os.path, sys

from epubmangler import EPub, is_epub

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, GdkPixbuf


def scale_cover(file, allocation):
    height = allocation.height 
    width = allocation.width / 3
    return GdkPixbuf.Pixbuf.new_from_file_at_scale(file, width, height, True)

def edit_date(calendar, entry):
    pass

def add_subject(entry, list_model, popover):
    list_model.append([entry.get_text()])
    entry.set_text('')
    popover.popdown()


if __name__ == '__main__':
    if len(sys.argv) > 1 and is_epub(sys.argv[1]):
        book = EPub(sys.argv[1])
    else:
        book = None
    
    builder = Gtk.Builder()
    builder.add_from_file('window.xml')
    
    window = builder.get_object('window')
    window.connect('destroy', Gtk.main_quit)
    window.show()

    cover = builder.get_object('cover')
    
    if book:
        builder.get_object('headerbar').show_all()
        builder.get_object('title_label').set_text(os.path.basename(book.file))
        window.set_title(os.path.basename(book.file))
        
        for field in ('title', 'creator', 'date', 'publisher', 'language'):
            try:
                builder.get_object(field).set_text(book.get(field).text)
            except NameError:
                pass
        
        calendar = builder.get_object('calendar')
        date_entry = builder.get_object('date')
        calendar.connect('day-selected', edit_date, date_entry)
        date_entry.connect('icon-press', lambda _entry, _icon, _event, popover: popover.popup(),
                           builder.get_object('popovercalendar'))
        
        subject_view = builder.get_object('subjects')
        list_model = Gtk.ListStore(str)
        for subject in book.get_all('subject'):
            list_model.append([subject.text])
        subject_view.set_model(list_model)

        subject_entry = builder.get_object('subject_entry')
        subject_entry.connect('activate', add_subject, list_model, builder.get_object('popoverentry'))

        col = Gtk.TreeViewColumn('Subjects', Gtk.CellRendererText(), text=0)
        subject_view.append_column(col)

        try:
            buf = Gtk.TextBuffer()
            buf.set_text(book.get('description').text)
            builder.get_object('description').set_buffer(buf)
        except NameError:
            pass

        cover.set_from_pixbuf(scale_cover(book.get_cover(),
                                          builder.get_object('box').get_allocation()))
    
    else:
        builder.get_object('box').hide()

    Gtk.main()
