#!/usr/bin/env python
"""Test all EPub methods against a random book from Project Gutenberg."""

import os
import unittest
import random

from pathlib import Path

import xml.etree.ElementTree as ET

import epubmangler

# Select a book from local selection of epubs
DIR = '/home/david/Projects/epubmangler/books/gutenberg'
# DIR = '/home/david/Projects/epubmangler/books/calibre'
BOOKS = os.listdir(DIR)
BOOK = Path(DIR, random.choice(BOOKS))
FILENAME = 'testtesttest.epub'

# pylint: skip-file

class EPub2GutenbergTestCase(unittest.TestCase):

    def setUp(self):
        self.book = epubmangler.EPub(BOOK)

    def tearDown(self):
        if Path(FILENAME).exists():
            os.remove(FILENAME)

    def test_get(self):
        self.assertRaises(epubmangler.epub.EPubError, self.book.get, 'nothing')
        self.assertIsInstance(self.book.get('title'), ET.Element)

    def test_get_all(self):
        self.assertRaises(epubmangler.epub.EPubError, self.book.get_all, 'nothing')

        for item in self.book.get_all('date'):
            self.assertIsInstance(item, ET.Element)

    def test_get_cover(self):
        self.assertTrue(Path(self.book.get_cover()).exists())

    def test_save(self):
        self.book.save(FILENAME)
        self.assertTrue(Path(FILENAME).exists())
        self.assertRaises(FileExistsError, self.book.save, FILENAME)
        os.remove(FILENAME)

    def test_add(self):
        els = self.book.get_all('date')
        for el in els:
            self.book.add(el.tag, 'ddd', el.attrib)

    def test_set(self):
        self.book.set('title', 'something')
        self.assertEqual('something', self.book.get('title').text)

        self.book.set('creator', 'someone', {'ddd': 'zzz'})
        self.assertEqual('someone', self.book.get('creator').text)
        self.assertEqual('zzz', self.book.get('creator').attrib['ddd'])
        self.book.set('creator', 'aaa', {'ddd': 'zzz'})

        self.assertRaises(epubmangler.epub.EPubError, self.book.set, 'nope', 'nope')

        self.book.set('language', 'en', {'xsi:type': 'dcterms:RFC4646'})

    def test_set_cover(self):
        self.book.set_cover('example/cat_picture.jpg')

    def test_set_identifier(self):
        self.book.set_identifier('1234567890', 'isbn')
        self.assertEqual(self.book.get('identifier').text, '1234567890')
        self.assertEqual(self.book.get('identifier').attrib['opf:scheme'], 'isbn')

    def test_remove(self):
        self.book.remove('title')
        self.assertRaises(epubmangler.epub.EPubError, self.book.get, 'title')

    def test_add_remove_subject(self):
        len1 = len(self.book.get_all('subject'))
        self.book.add_subject('zzz')
        len2 = len(self.book.get_all('subject'))
        self.assertGreater(len2, len1)
        self.book.remove_subject('zzz')
        len3 = len(self.book.get_all('subject'))
        self.assertLess(len3, len2)

    def test_setitem(self):
        self.book['title'] = 'zzzz'
        self.assertEqual(self.book.get('title').text, 'zzzz')
        self.book['description'] = 'zzzz'
        self.assertEqual(self.book['description'].text, 'zzzz')

    def test_getitem(self):
        self.assertIsInstance(self.book['title'], ET.Element)
        try:
            self.book['nothing']
        except epubmangler.epub.EPubError:
            pass

    def test_context_handler(self):
        with epubmangler.EPub(BOOK) as _book:
            pass

    def test_init(self):
        self.assertRaises(epubmangler.epub.EPubError, epubmangler.EPub, 'notafile')
        # TODO: Need some bad epub files to test here


if __name__ == '__main__':
    print(BOOK.name)
    unittest.main(verbosity=2)
