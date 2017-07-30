

import argparse
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.0')

from ui import Window
from parse import EPub

def main():
    parser = argparse.ArgumentParser(prog='epubmangler', description='Modify epub metadata.')
    parser.add_argument('file', metavar='FILE', help='the path to an epub file')
    args = parser.parse_args()

    if args.file:
        Window(EPub(args.file, debug=True))
        gi.repository.Gtk.main()

if __name__ == '__main__':
    main()
    