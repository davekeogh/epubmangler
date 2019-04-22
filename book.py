# A second try at a readable, editable ebook class


import os, os.path, shutil, tempfile, time, zipfile
import xml.etree.ElementTree as ETree


class SerializationFailedError(Exception):
    pass


class EBook(dict):


    file_path = ''

    
    def __init__(self, path, debug=False):
        self.file_path = path

        if debug: self._EBook__debug()
    

    def __del__(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


    def __debug(self):
        pass


    def extract(self):
        self.temp_dir = tempfile.mkdtemp()

        try:
            with zipfile.ZipFile(self.file_path) as myzip:
                myzip.extractall(self.temp_dir)
        except zipfile.BadZipfile:
            raise SerializationFailedError('{} is not an epub file'.format(self.file_path))

        for root, dirs, names in os.walk(self.temp_dir):
            for name in names:
                self.files.append(os.path.join(root, name))

        if os.path.exists(os.path.join(self.temp_dir, 'OEBPS')):
            self.files_root = os.path.join(self.temp_dir, 'OEBPS')
        else:
            self.files_root = self.temp_dir


class EPub(EBook):
    pass


class Mobi(EBook):
    pass


class AZW3(EBook):
    pass
