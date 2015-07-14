import sys
from gi.repository import Gtk
from ui import Window
from parse import EPub


if __name__ == '__main__':
    win = Window(EPub(sys.argv[1], debug=True))
    Gtk.main()
