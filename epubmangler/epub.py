"""EPub is a Python object that represents the metadata of an .epub file."""


# Useful links:
# http://idpf.org/epub/30/spec/epub30-ocf.html
# http://idpf.org/epub/20/spec/OPF_2.0_final_spec.html
# https://www.dublincore.org/specifications/dublin-core/dcmi-terms/

# https://wiki.mobileread.com/wiki/Dublin_Core
# https://wiki.mobileread.com/wiki/OPF

# https://docs.python.org/3/library/xml.etree.elementtree.html


from __future__ import annotations

import mimetypes
import os
import os.path
import shutil
import time

import xml.etree.ElementTree as ET

from tempfile import TemporaryDirectory as TempDir
from types import TracebackType
from typing import Dict, List, Optional, Type
from zipfile import ZipFile, ZIP_DEFLATED

from .globals import XPATHS, ILLEGAL_CHARS, NAMESPACES, IMAGE_TYPES
from .functions import find_opf_files, is_epub, strip_namespaces


class EPub:
    """A Python object representing an epub ebook's editable metadata."""

    etree: ET.ElementTree
    file: str
    tempdir: TempDir
    version: str


    def __init__(self, path: str) -> None:
        """Open an epub file and load its metadata into memory for editing."""

        self.tempdir = None

        if not is_epub(path):
            raise ValueError(f"{path} does not appear to be a valid .epub file.")

        self.file = path
        self.tempdir = TempDir(prefix='epubmangler-')

        with ZipFile(self.file, 'r', ZIP_DEFLATED) as zip_file:
            zip_file.extractall(self.tempdir.name)

        try:
            self.etree = ET.parse(find_opf_files(self.tempdir.name)[0])
            self.version = self.etree.getroot().attrib['version']
        except IndexError:
            raise ValueError(f"{path} does not appear to be a valid .epub file.")
        except ET.ParseError:
            raise ValueError(f"{path} does not appear to be a valid .epub file.")


    def __del__(self) -> None:

        if self.tempdir:
            self.tempdir.cleanup()


    # The next two methods enable context manager support
    def __enter__(self) -> EPub:

        return self


    def __exit__(self, _type: Optional[Type[BaseException]], _value: Optional[BaseException],
                 _traceback: Optional[TracebackType]) -> bool:

        self.__del__()
        return False # Raise any thrown exception before exiting


    # The next two methods make the object subscriptable like a Dict
    def __getitem__(self, name: str) -> ET.Element:

        return self.get(name)


    def __setitem__(self, name: str, text: str) -> None:

        try:
            self.get(name).text = text
        except AttributeError:
            self.add(name, text)


    def add(self, name: str, text: str = None, attrib: Dict[str, str] = None) -> None:
        """Adds a new element to the metadata section of the tree."""

        for meta in self.get_all(name):
            if strip_namespaces(meta.attrib) == attrib:
                raise AttributeError(f"{os.path.basename(self.file)} already has an \
                                     identical element. It is usually incorrect to have \
                                     more than one of most elements.")

        element = ET.Element(f"dc:{name}", attrib) # Add the dc: namespace to everything?
        element.text = text

        self.etree.find('./opf:metadata', NAMESPACES).append(element)


    def add_subject(self, name: str) -> bool:
        """Adds a subject to the tree. This will return False if the subject already exists."""

        for meta in self.get_all('subject'):
            if meta.text == name:
                return False


        element = ET.Element('dc:subject')
        element.text = name

        self.etree.find('./opf:metadata', NAMESPACES).append(element)

        return True


    def get(self, name: str) -> ET.Element:
        """This will return the first matching element. Use get_all if you expect
        multiple elements to exist. There are usually several subject tags for instance."""

        element = None

        try:
            xpaths = XPATHS[name]
        except KeyError:
            raise AttributeError(f"{os.path.basename(self.file)} has no element: '{name}'")

        for xpath in xpaths:
            element = self.etree.getroot().find(xpath, NAMESPACES)
            if element is not None:
                break

        if element is None:
            raise AttributeError(f"{os.path.basename(self.file)} has no element: '{name}'")

        return element


    def get_all(self, name: str) -> List[ET.Element]:
        """Returns a list of all the matching elements. There are often multiple date
        and subject tags for instance."""

        elements = []

        try:
            xpaths = XPATHS[name]
        except KeyError:
            raise AttributeError(f"{os.path.basename(self.file)} has no element: '{name}'")

        for xpath in xpaths:
            for element in self.etree.getroot().findall(xpath, NAMESPACES):
                if element is not None:
                    elements.append(element)

        if not elements:
            raise AttributeError(f"{os.path.basename(self.file)} has no element: '{name}'")

        return elements


    def get_cover(self) -> str:
        """Returns the full path of the cover image in the temporary directory.
        The cover is slightly more involved to edit than other items. We need to look at the
        attribs of two different tags to get the file name.

        `./opf:metadata/opf:meta/[@name="cover"]` gives us an element with an `id` attrib

        `./opf:manifest/opf:item/[@id=id]` gives us an element with a `href` element that points to
        the cover file, the `media-type` attrib also needs to be set if the file type changed."""

        id_num = self.get_all('cover')[0].attrib['content']
        name = self.etree.getroot().find(f"./opf:manifest/opf:item/[@id=\"{id_num}\"]",
                                         NAMESPACES).attrib['href']

        based = os.path.split(find_opf_files(self.tempdir.name)[0])[0]

        return os.path.join(based, name)


    def remove(self, name: str, attrib: Dict[str, str] = None) -> None:
        """Removes an element from the tree. Books can have more than one date or creator element.
        Use attrib to get extra precision in these cases."""

        elements = self.get_all(name)

        if attrib:
            for element in elements:
                if attrib == strip_namespaces(element.attrib):
                    self.etree.find('./opf:metadata', NAMESPACES).remove(element)

        else:
            self.etree.find('./opf:metadata', NAMESPACES).remove(elements[0])


    def remove_subject(self, name: str) -> None:
        """Removes a subject element from the tree."""

        for subject in self.get_all('subject'):
            if subject.text == name:
                self.etree.find('./opf:metadata', NAMESPACES).remove(subject)


    def set(self, name: str, text: str = None, attrib: Dict[str, str] = None) -> None:
        """Sets the text and attribs of a element."""

        if not attrib:
            element = self.get(name)
            element.text = text

        else:
            elements = self.get_all(name)

            if not elements:
                raise AttributeError(f"{os.path.basename(self.file)} has no {name} element.")

            for element in elements:
                if attrib == strip_namespaces(element.attrib):
                    element.text = text
                    break


    def set_cover(self, path: str) -> None:
        """Replaces the cover image of the book with `path` provided it is an image."""

        cover = self.get_cover()
        based = os.path.split(find_opf_files(self.tempdir.name)[0])[0]
        name = os.path.basename(path)
        mime = mimetypes.guess_type(path)[0]

        if mime in IMAGE_TYPES and os.path.exists(path):
            id_num = self.get_all('cover')[0].attrib['content']
            element = self.etree.getroot().find(f"./opf:manifest/opf:item/[@id=\"{id_num}\"]",
                                                NAMESPACES)

            element.attrib['media-type'] = mime
            element.attrib['href'] = name

            shutil.copy(path, os.path.join(based, name))
            os.remove(cover)


    def set_identifier(self, name: str, scheme: str = None) -> None:
        """Sets the epub's ID metadata. This is generally the book's ISBN or a URI."""

        id_num = self.etree.getroot().attrib['unique-identifier']
        element = self.etree.getroot().find(f"./opf:metadata/dc:identifier/[@id=\"{id_num}\"]",
                                            NAMESPACES)

        element.text = name

        if not scheme: # TODO: Improve this detection
            if name.startswith('http'):
                scheme = 'URI'
            if name.startswith('doi:'):
                scheme = 'DOI'
            else:
                scheme = 'ISBN'

        element.attrib['opf:scheme'] = scheme

        # Work around ElementTree issue: https://bugs.python.org/issue17088 (See comment in save)
        del element.attrib[f"{{{NAMESPACES['opf']}}}scheme"]


    def save(self, path: str, overwrite: bool = False) -> None:
        """Saves the opened EPub with the modified metadata to the file specified in path.
        If you want to overwrite an existing file set overwrite=True."""

        # Remove some characters that could cause file system errors
        # This is mostly useful if you rename a file to the book title etc.
        dirname, basename = os.path.split(path)

        for char in ILLEGAL_CHARS:
            basename.replace(char, '-')

        path = os.path.join(dirname, basename)

        if os.path.exists(path) and not overwrite:
            raise FileExistsError(f"{path} already exists. Use overwrite=True if you're serious.")

        self.add('date', time.strftime('%Y-%m-%d'), {'event' : 'modified'})

        name = os.path.join(self.tempdir.name, find_opf_files(self.tempdir.name)[0])
        self.etree.write(name, xml_declaration=True, encoding='utf-8', method='xml')

        # Work around an old issue in ElementTree:
        # ElementTree incorrectly refuses to write attributes without namespaces
        # when default_namespace is used
        # https://bugs.python.org/issue17088
        # https://github.com/python/cpython/pull/11050

        text = open(name, 'r').read()
        text = text.replace('ns0:', '')
        text = text.replace(':ns0', ':opf')
        text = text.replace('<package ', '<package xmlns=\"http://www.idpf.org/2007/opf\" ')

        with open(name, 'w') as opf:
            opf.write(text)

        # TODO: Tidy XML before zip?
        # ElementTree has an indent function in Python 3.9, use that?

        with ZipFile(path, 'w', ZIP_DEFLATED) as zip_file:
            for root, _dirs, files in os.walk(self.tempdir.name):
                for name in files:
                    full_path = os.path.join(root, name)
                    zip_file.write(full_path, os.path.relpath(full_path, self.tempdir.name))
