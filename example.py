#!/usr/bin/env python
"""Example usage of the epub module to edit the metadata of an ebook."""

from epub import EPub

with EPub('data/Frankenstein.epub') as book: # https://gutenberg.org/ebooks/84

    # Get information about a book
    language = book.get('language')
    subjects = book.get_all('subject')

    # Modify existing elements
    book.set('title', 'Frankenstein 2')

    # Add and remove elements
    book.add('creator', 'David Keogh', {'opf:role' : 'adapter'})
    book.remove('date', {'opf:event' : 'conversion'})

    # Convenience functions
    book.set_cover('data/cat picture.jpg')
    book.set_identifier('http://github.com/davekeogh/epubmangler', 'URI')

    # Add and remove subjects
    book.add_subject('Sequel')
    book.add_subject('Comedy')
    book.remove_subject('Horror tales')

    book.save('data/Frankenstein 2.epub', overwrite=True)
