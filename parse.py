import zipfile
import os
import os.path
import tempfile
import shutil
import collections
import xml.etree.ElementTree as ETree
from globals import *


EPubMetadata = collections.namedtuple('EPubMetadata', 'tag attrib text')


class BadEPubFile(Exception):
    pass


class EPub(object):

    def __init__(self, path, debug=False):
        self.save_changes = False
        self.file_path = path
        self.temp_dir = ''
        self.temp_cover = ''
        self.files = ()
        self.tree = None
        self.root = None
        self.fields = []
        self.manifest = []

        self.title = ''
        self.author = ''
        self.publisher = ''
        self.date = ''

        self.extract()
        self.read_content()

        if debug:
            self.debug()

    def __del__(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def extract(self):
        self.temp_dir = tempfile.mkdtemp()

        try:
            with zipfile.ZipFile(self.file_path) as myzip:
                myzip.extractall(self.temp_dir)
        except zipfile.BadZipfile:
            raise BadEPubFile('File is not an epub file')

        self.files = os.walk(self.temp_dir)

    def read_content(self):
        self.tree = ETree.parse(os.path.join(self.temp_dir, 'content.opf'))
        self.root = self.tree.getroot()

        metadata = self.root.findall('{}metadata'.format(OPF_NAMESPACE))

        if len(metadata) > 1:
            raise BadEPubFile('Malformed XML file')

        for item in metadata[0]:
            self.fields.append(EPubMetadata(tag=item.tag, attrib=item.attrib, text=item.text))

            if item.tag == '{}title'.format(DC_NAMESPACE):
                self.title = item.text
            elif item.tag == '{}creator'.format(DC_NAMESPACE) and item.attrib.get('{}role'.format(OPF_NAMESPACE)) == 'aut':
                self.author = item.text
            elif item.tag == '{}publisher'.format(DC_NAMESPACE):
                self.publisher = item.text
            elif item.tag == '{}date'.format(DC_NAMESPACE):
                self.date = item.text

        manifest = self.root.findall('{}manifest'.format(OPF_NAMESPACE))

        if len(manifest) > 1:
            raise BadEPubFile('Malformed XML file')

        for item in manifest[0]:
            self.manifest.append(EPubMetadata(tag=item.tag, attrib=item.attrib, text=item.text))

            if item.attrib['id'] == 'cover':
                self.temp_cover = os.path.join(self.temp_dir, item.attrib['href'])

    def debug(self):
        print(self.file_path)

        print('\nMetadata:')

        for i in self.fields:
            print(i.tag, i.attrib, i.text)

        print('\nManifest:')

        for i in self.manifest:
            print(i.tag, i.attrib, i.text)

        print('\nFiles:')

        for f in self.files:
            print(f)

    def set(self, tag, attrib=None, text=None):
        namespaced_tag = '{0}{1}'.format(DC_NAMESPACE, tag)
