"""Unit tests for epubmangler"""

from epubmangler.epub import EPub
import os
import os.path
import unittest

import xml.etree.ElementTree as ET

import epubmangler


BOOK = 'Frankenstein.epub'


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
    
    def test_set(self):
        self.book.set('title', 'something')
        self.assertEqual('something', self.book.get('title').text)

        self.book.set('creator', 'someone', {'ddd' : 'zzz'})
        self.assertEqual('someone', self.book.get('creator').text)
        self.assertEqual('zzz', self.book.get('creator').attrib['ddd'])

        self.book.set('creator', 'a long name with many parts', {'opf:file-as' : 'zzz'})
        self.assertEqual('zzz', self.book.get('creator').attrib['opf:file-as'])

        self.assertRaises(NameError, self.book.set, 'nope', 'nope')

        self.book.set('language', 'en', {'xsi:type' : 'dcterms:RFC4646'})

    def test_set_cover(self):
        self.book.set_cover('cat_picture.jpg')
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
    
    def test_remove_subject(self):
        subject = self.book.get_all('subject')[0]
        self.book.remove_subject(subject.text)
        self.assertNotEqual(subject.text, self.book.get_all('subject')[0])
    
    def test_add_subject(self):
        subject = self.book.get_all('subject')[0]
        self.book.add_subject('zzz')
        self.assertNotEqual(subject.text, self.book.get_all('subject')[0])
    
    def test_setitem(self):
        self.book['title'] = 'zzzz'
        self.assertEqual(self.book.get('title').text, 'zzzz')
        self.book['description'] = 'zzzz'
        self.assertEqual(self.book.get('description').text, 'zzzz')
    
    def test_getitem(self):
        self.assertIsInstance(self.book['title'], ET.Element)
        try:
            self.book['nothing']
        except NameError:
            pass

    def test_context_handler(self):
        with EPub('Frankenstein.epub') as _e:
            pass
    
    def test_init(self):
        self.assertRaises(ValueError, EPub, 'notafile')
        # TODO: Need some bad epub files to test here

if __name__ == '__main__':
    unittest.main()
