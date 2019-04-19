import zipfile
import os
import os.path
import tempfile
import shutil
import collections
import time
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
        self.files = []
        self.files_root = ''
        self.tree = None
        self.root = None
        self.fields = []
        self.manifest = []
        self.name = os.path.split(path)[1]

        self.title = ''
        self.author = ''
        self.publisher = ''
        self.date = None
        self.series = ''
        self.series_index = 1
        self.description = ''

        self.debug_information = ''

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

        for root, dirs, names in os.walk(self.temp_dir):
            for name in names:
                self.files.append(os.path.join(root, name))

        if os.path.exists(os.path.join(self.temp_dir, 'OEBPS')):
            self.files_root = os.path.join(self.temp_dir, 'OEBPS')
        else:
            self.files_root = self.temp_dir

    def read_content(self):
        self.tree = ETree.parse(os.path.join(self.files_root, 'content.opf'))
        self.root = self.tree.getroot()

        metadata = self.root.findall('{}metadata'.format(OPF_NAMESPACE))

        if len(metadata) > 1:
            raise BadEPubFile('Malformed XML file')

        for item in metadata[0]:
            self.fields.append(EPubMetadata(tag=item.tag, attrib=item.attrib, text=item.text))

            if item.tag == '{}title'.format(DC_NAMESPACE):
                self.title = item.text
            elif item.tag == '{}creator'.format(DC_NAMESPACE) and item.attrib.get(
                    '{}role'.format(OPF_NAMESPACE)) == 'aut':
                self.author = item.text
            elif item.tag == '{}publisher'.format(DC_NAMESPACE):
                self.publisher = item.text
            elif item.tag == '{}date'.format(DC_NAMESPACE) and item.attrib.get(
                    '{}event'.format(OPF_NAMESPACE)) != 'modification':
                try:
                    self.date = time.strptime(item.text, '%Y-%m-%dT%H:%M:%S+00:00')
                except ValueError:
                    self.date = time.strptime(item.text, '%Y-%m-%d')
            elif item.tag == '{}meta'.format(OPF_NAMESPACE) and item.attrib.get('name') == 'calibre:series':
                self.series = item.attrib.get('content')
            elif item.tag == '{}meta'.format(OPF_NAMESPACE) and item.attrib.get('name') == 'calibre:series_index':
                self.series_index = int(item.attrib.get('content'))
            elif item.tag == '{}description'.format(DC_NAMESPACE):
                self.description = item.text

        manifest = self.root.findall('{}manifest'.format(OPF_NAMESPACE))

        if len(manifest) > 1:
            raise BadEPubFile('Malformed XML file')

        for item in manifest[0]:
            self.manifest.append(EPubMetadata(tag=item.tag, attrib=item.attrib, text=item.text))

            if item.attrib['id'] == 'cover':
                self.temp_cover = os.path.join(self.files_root, item.attrib['href'])

    def get_date_as_string(self):
        return '{} - {} - {}'.format(self.date.tm_year, self.date.tm_mon, self.date.tm_mday)

    def set_date_for_export(self, date):
        self.date = '{}T00:00:00+00:00'.format(date)

    def update_tags(self, tags):
        new = []

        for item in self.fields:
            if item.tag != '{}subject'.format(DC_NAMESPACE):
                new.append(item)

        for tag in tags:
            new.append(EPubMetadata(tag='{}subject'.format(DC_NAMESPACE), attrib={}, text=tag))

        self.fields = new

    def update_fields(self):
        for item in self.fields:
            if item.tag == '{}title'.format(DC_NAMESPACE):
                item.text = self.title
            elif item.tag == '{}creator'.format(DC_NAMESPACE) and item.attrib.get(
                    '{}role'.format(OPF_NAMESPACE)) == 'aut':
                item.text = self.author
            elif item.tag == '{}publisher'.format(DC_NAMESPACE):
                item.text = self.publisher
            elif item.tag == '{}date'.format(DC_NAMESPACE) and item.attrib.get(
                    '{}event'.format(OPF_NAMESPACE)) != 'modification':
                item.text = self.date
            elif item.tag == '{}meta'.format(OPF_NAMESPACE) and item.attrib.get('name') == 'calibre:series':
                item.text = self.series
            elif item.tag == '{}meta'.format(OPF_NAMESPACE) and item.attrib.get('name') == 'calibre:series_index':
                item.text = str(self.series_index)
        
    def serialize(self, filename):
        manifest = self.root.findall('{}manifest'.format(OPF_NAMESPACE))
        metadata = self.root.findall('{}metadata'.format(OPF_NAMESPACE))

        for item in metadata[0]:
            if item.tag == '{}title'.format(DC_NAMESPACE):
                item.text = self.title
            elif item.tag == '{}creator'.format(DC_NAMESPACE) and item.attrib.get(
                    '{}role'.format(OPF_NAMESPACE)) == 'aut':
                item.text = self.author
            elif item.tag == '{}publisher'.format(DC_NAMESPACE):
                item.text = self.publisher
            elif item.tag == '{}date'.format(DC_NAMESPACE) and item.attrib.get(
                    '{}event'.format(OPF_NAMESPACE)) != 'modification':
                item.text == self.date
            elif item.tag == '{}meta'.format(OPF_NAMESPACE) and item.attrib.get('name') == 'calibre:series':
                item.text = self.series
            elif item.tag == '{}meta'.format(OPF_NAMESPACE) and item.attrib.get('name') == 'calibre:series_index':
                item.text = str(self.series_index)
            elif item.tag == '{}description'.format(DC_NAMESPACE):
                item.text = self.description
            elif item.tag == '{}subject'.format(DC_NAMESPACE):
                metadata[0].remove(item)
        
        for item in self.fields:
            if item.tag == '{}subject'.format(DC_NAMESPACE):
                el = ETree.Element(item.tag, attrib=item.attrib, text=item.text)
                metadata[0].append(el)

        self.tree.write(tempfile.mkstemp()[1])

        self.package_epub(filename)
    
    def package_epub(self, filename):
        new_dir = tempfile.mkdtemp()

    def debug(self):
        data = '\nMetadata:\n\n'

        for i in self.fields:
            data += '{}, {}, {}\n\n'.format(i.tag, i.attrib, i.text)

        data += '\n\nManifest:\n\n'

        for i in self.manifest:
            data += '{}, {}, {}\n\n'.format(i.tag, i.attrib, i.text)

        data += '\n\nFiles:\n\n'

        for f in self.files:
            data += '{}\n'.format(f)

        self.debug_information = data

    def set(self, tag, attrib=None, text=None):
        namespaced_tag = '{0}{1}'.format(DC_NAMESPACE, tag)

        for item in self.fields:
            if item.tag == namespaced_tag:
                item.tag = namespaced_tag
                if attrib:
                    item.attrib = attrib
                if text:
                    item.text = text
                break
