#!/usr/bin/env python
"""Test all EPub methods against a random book from Project Gutenberg."""

import os, os.path, unittest, random

import xml.etree.ElementTree as ET

import epubmangler

# Select a book from local selection of epubs
DIR = 'books/gutenberg'
# DIR = 'books/calibre'
BOOKS = os.listdir(DIR)
BOOK = os.path.join(DIR, random.choice(BOOKS))


class EPub2GutenbergTestCase(unittest.TestCase):

    def setUp(self):
        self.book = epubmangler.EPub(BOOK)
    
    def test_get(self):
        self.assertRaises(NameError, self.book.get, 'nothing')
        self.assertIsInstance(self.book.get('title'), ET.Element)
    
    def test_get_all(self):
        self.assertRaises(NameError, self.book.get_all, 'nothing')
        
        for item in self.book.get_all('date'):
            self.assertIsInstance(item, ET.Element)
    
    def test_get_cover(self):
        self.assertTrue(os.path.exists(self.book.get_cover()))
    
    def test_save(self):
        name = 'testtesttest.epub'
        self.book.save(name)
        self.assertTrue(os.path.exists(name))
        self.assertRaises(FileExistsError, self.book.save, name)
        os.remove(name)
    
    def test_add(self):
        els = self.book.get_all('date')
        for el in els:
            self.book.add(el.tag, 'ddd', el.attrib)
    
    def test_set(self):
        self.book.set('title', 'something')
        self.assertEqual('something', self.book.get('title').text)

        self.book.set('creator', 'someone', {'ddd' : 'zzz'})
        self.assertEqual('someone', self.book.get('creator').text)
        self.assertEqual('zzz', self.book.get('creator').attrib['ddd'])
        self.book.set('creator', 'aaa', {'ddd' : 'zzz'})

        self.book.set('creator', 'a long name with many parts')
        self.assertEqual('parts, a long name with many', self.book.get('creator').attrib['opf:file-as'])

        self.assertRaises(NameError, self.book.set, 'nope', 'nope')

        self.book.set('language', 'en', {'xsi:type' : 'dcterms:RFC4646'})

    def test_set_cover(self):
        self.book.set_cover('example/cat_picture.jpg')
        self.assertEqual(os.path.basename(self.book.get_cover()), 'cat_picture.jpg')
    
    def test_set_identifier(self):
        self.book.set_identifier('1234567890', 'isbn')
        self.assertEqual(self.book.get('id').text, '1234567890')
        self.assertEqual(self.book.get('id').attrib['opf:scheme'], 'isbn')
    
    def test_remove(self):
        self.book.remove('title')
        self.assertRaises(NameError, self.book.get, 'title')

        dates1 = len(self.book.get_all('date'))
        self.book.remove('date', {'event' : 'conversion'})
        
        try:
            dates2 = len(self.book.get_all('date'))
            self.assertTrue(dates1 > dates2)
        except NameError:
            pass
    
    def test_add_remove_subject(self):
        len1 = len(self.book.get_all('subject'))
        self.book.add_subject('zzz')
        len2 = len(self.book.get_all('subject'))
        self.assertGreater(len2, len1)
        self.book.remove_subject('zzz')
        len3 = len(self.book.get_all('subject'))
        self.assertLess(len3, len2)

        try:
            sub1 = self.book.get_all('subject')[0]
            self.assertFalse(self.book.add_subject(sub1.text))
        except KeyError:
            pass

    def test_setitem(self):
        self.book['title'] = 'zzzz'
        self.assertEqual(self.book.get('title').text, 'zzzz')
        self.book['description'] = 'zzzz'
        self.assertEqual(self.book['description'].text, 'zzzz')
    
    def test_getitem(self):
        self.assertIsInstance(self.book['title'], ET.Element)
        try:
            self.book['nothing']
        except NameError:
            pass

    def test_context_handler(self):
        with epubmangler.EPub(BOOK) as _e:
            pass
    
    def test_init(self):
        self.assertRaises(ValueError, epubmangler.EPub, 'notafile')
        # TODO: Need some bad epub files to test here


if __name__ == '__main__':
    print(os.path.basename(BOOK))
    unittest.main(verbosity=2)
