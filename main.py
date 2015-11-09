import sys
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.0')

from ui import Window
from parse import EPub


win = Window(EPub(sys.argv[1], debug=True))
gi.repository.Gtk.main()
