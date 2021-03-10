#!/usr/bin/env python
"""Grab all the epub files from a directory tree and copy them to 
./calibre"""

import os, os.path, shutil, sys

from epubmangler import is_epub

PATH = '/home/david/Dropbox/Calibre Library'
EPUBS = []

for root, dirs, files in os.walk(PATH):
    for name in files:
        full_name = os.path.join(root, name)
        if is_epub(full_name):
            EPUBS.append(full_name)

for epub in EPUBS:
    if os.path.isdir(sys.argv[len(sys.argv) - 1]):
        PATH = sys.argv[len(sys.argv) - 1]

    full_name = os.path.join('calibre', os.path.basename(epub))

    if not os.path.exists(full_name):
        shutil.copy(epub, full_name)
