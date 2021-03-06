"""Unit tests for epubmangler"""

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
        os.remove(name)
    
    def test_set(self):
        self.book.set('title', 'something')
        self.assertEqual('something', self.book.get('title').text)

        self.book.set('creator', 'someone', {'ddd' : 'zzz'})
        self.assertEqual('someone', self.book.get('creator').text)
        self.assertEqual('zzz', self.book.get('creator').attrib['ddd'])

        self.assertRaises(NameError, self.book.set, 'nope', 'nope')

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


if __name__ == '__main__':
    unittest.main()
