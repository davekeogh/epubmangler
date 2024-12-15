#!/usr/bin/env python
"""Rename epub files in a directory to `author - title.epub`."""

import os
import sys
import timeit

from pathlib import Path
from epubmangler import EPub, EPubError, is_epub, ILLEGAL_CHARS


def rename_file(in_file: str | bytes | os.PathLike) -> None:
    """Rename file to its EPub metadata or return."""

    try:
        book = EPub(in_file)
    except EPubError:
        return

    try:
        title = book.get('title').text
        author = book.get('creator').text
    except NameError:
        print(f'No title or author metadata: {in_file}')
        return

    file_name = f'{author} - {title}.epub'

    # Some characters are not allowed in filenames, especially on Windows
    for char in ILLEGAL_CHARS:
        file_name = file_name.replace(char, '-')

    new_file = Path(file_name)

    if new_file != in_file:
        os.rename(in_file, new_file)


if __name__ == '__main__':

    if len(sys.argv) > 1 and Path(sys.argv[1]).is_dir():
        DIR = sys.argv[1]
    else:
        DIR = os.getcwd()

    FILES = 0
    TIME = 0

    for file in os.listdir(DIR):
        if is_epub(Path(DIR, file)):
            FILES += 1
            TIME += timeit.timeit(stmt='rename_file(path)',
                                  setup='from __main__ import rename_file, path',
                                  number=1)

    print(f'Read {FILES} files in {round(TIME, 3)}s')
