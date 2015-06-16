from gi.repository import Gtk
from ui import Window
from parse import EPub

if __name__ == '__main__':
    lel = EPub('The Stranger - Albert Camus.epub', debug=True)
    # lel = EPub('Jojo\'s Bizarre Adventure - Over Heaven - NisiOisin.epub', debug=True)

    win = Window(lel)
    Gtk.main()
