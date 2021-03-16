#!/usr/bin/env python
"""Rename epub files in a directory to `author - title.epub`."""

import os
import os.path
import sys

from epubmangler import EPub, is_epub, ILLEGAL_CHARS

if __name__ == '__main__':

    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        DIR = sys.argv[1]
    else:
        DIR = os.getcwd()

    for file in os.listdir(DIR):
        full_path = os.path.join(DIR, file)

        if is_epub(full_path):
            book = EPub(full_path)
            
            try:
                title = book.get('title').text
                author = book.get('creator').text
            except NameError:
                print(f'No title or author metadata: {file}')
                continue

            file_name = f'{author} - {title}.epub'

            # Some characters are not allowed in filenames especially on Windows
            for char in ILLEGAL_CHARS:
                file_name = file_name.replace(char, '-')

            new_file = os.path.join(DIR, file_name)

            if new_file != full_path:
                os.rename(full_path, new_file)
