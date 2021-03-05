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


if __name__ == '__main__':
    unittest.main()
