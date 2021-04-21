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

from .globals import XPATHS, ILLEGAL_CHARS, NAMESPACES, IMAGE_TYPES, TIME_FORMAT
from .functions import file_as, find_opf_files, is_epub, namespaced_text, strip_namespaces


class EPub:
    """A Python object representing an epub ebook's editable metadata."""

    etree: ET.ElementTree
    file: str
    metadata: List[ET.Element]
    opf: str
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
            self.opf = find_opf_files(self.tempdir.name)[0]
            self.etree = ET.parse(self.opf)
            self.version = self.etree.getroot().attrib['version']
            self.metadata = self.etree.getroot().findall('./opf:metadata/*', NAMESPACES)
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
        except NameError:
            self.add(name, text)


    def add(self, name: str, text: str = None, attrib: Dict[str, str] = None) -> None:
        """Adds a new element to the metadata section of the tree."""

        try:
            for meta in self.get_all(name):
                if strip_namespaces(meta.attrib) == strip_namespaces(attrib):
                    raise NameError(f"{os.path.basename(self.file)} already has an \
                                        identical element. It is usually incorrect to have \
                                        more than one of most elements.")
        except NameError:
            pass

        element = ET.Element(namespaced_text(f'dc:{name}')) # Add the dc: namespace to everything?
        element.text = text
        if attrib:
            element.attrib = attrib
        
        if name == 'creator':
            if attrib:
                element.attrib['opf:file-as'] = file_as(text)
            else:
                element.attrib = {'opf:file-as' : file_as(text)}

        self.etree.find('./opf:metadata', NAMESPACES).append(element)


    def add_subject(self, name: str) -> bool:
        """Adds a subject to the tree. This will return False if the subject already exists."""

        for subject in self.get_all('subject'):
            if subject.text == name:
                return False

        element = ET.Element(namespaced_text('dc:subject'))
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
            raise NameError(f"Unrecognized element: '{name}'")

        for xpath in xpaths:
            element = self.etree.getroot().find(xpath, NAMESPACES)
            if element is not None:
                break

        if element is None:
            raise NameError(f"{os.path.basename(self.file)} has no element: '{name}'")

        return element


    def get_all(self, name: str) -> List[ET.Element]:
        """Returns a list of all the matching elements. There are often multiple date
        and subject tags for instance."""

        elements: List[ET.Element]

        try:
            xpaths = XPATHS[name]
        except KeyError:
            raise NameError(f"Unrecognized element: '{name}'")

        for xpath in xpaths:
            # ET.Element evaluates as False so we need test that element is not None
            elements = map(lambda e: e if e is not None else False,
                           self.etree.getroot().findall(xpath, NAMESPACES))

        return elements

    def get_cover(self) -> str:
        """Returns the full path of the cover image in the temporary directory.
        
        `./opf:manifest/opf:item/[@properties=\"cover-image\"]` contains the local path to the
        image in EPub version 3 files.

        We need to look at the attribs of two different tags to get the file name for EPub 2 files:

        `./opf:metadata/opf:meta/[@name="cover"]` gives us an element with an `content` attrib

        `./opf:manifest/opf:item/[@id=content]` gives us an element with a `href` element that points to
        the cover file, the `media-type` attrib also needs to be set if the file type changed."""

        # EPub 3
        try:
            name = self.etree.getroot().find(f"./opf:manifest/opf:item/[@properties=\"cover-image\"]",
                                             NAMESPACES).attrib['href']
            based = os.path.split(find_opf_files(self.tempdir.name)[0])[0]
            
            return os.path.join(based, name)

        except AttributeError:
            pass

        # EPub 2
        # Some epubs found in the wild, that have been edited(?), have an extra <meta name="cover">
        # element leftover. We look at all of them until we find a matching item in the manifest.
        for item in self.get_all('cover'):
            id_tag = item.attrib['content']

            if id_tag is not None:
                try:
                    name = self.etree.getroot().find(f"./opf:manifest/opf:item/[@id=\"{id_tag}\"]",
                                                    NAMESPACES).attrib['href']

                    based = os.path.split(find_opf_files(self.tempdir.name)[0])[0]

                    return os.path.join(based, name)
                except AttributeError:
                    pass
        
        # No cover image 
        return None


    def remove(self, name: str, attrib: Dict[str, str] = None) -> None:
        """Removes an element from the tree. Books can have more than one date or creator element.
        Use attrib to get extra precision in these cases."""

        elements = self.get_all(name)

        if attrib:
            for element in elements:
                if attrib == strip_namespaces(element.attrib):
                    self.etree.getroot().find('./opf:metadata', NAMESPACES).remove(element)

        else:
            self.etree.getroot().find('./opf:metadata', NAMESPACES).remove(elements[0])


    def remove_subject(self, name: str) -> None:
        """Removes a subject element from the tree."""

        for subject in self.get_all('subject'):
            if subject.text == name:
                self.etree.getroot().find('./opf:metadata', NAMESPACES).remove(subject)


    def set(self, name: str, text: str = None, attrib: Dict[str, str] = None) -> None:
        """Sets the text and attribs of an element."""

        if name == 'creator':
            if not attrib:
                attrib = {}
            attrib['opf:file-as'] = file_as(text)

        if not attrib:
            element = self.get(name)
            element.text = text

        else:
            elements = self.get_all(name)
            found = False
            
            for element in elements:
                if strip_namespaces(attrib) == strip_namespaces(element.attrib):
                    element.text = text
                    found = True
                    break
            
            if not found:
                element = elements[0]
                element.text = text
                element.attrib = attrib


    def set_cover(self, path: str) -> None:
        """Replaces the cover image of the book with `path` provided it is an image."""

        based = os.path.split(find_opf_files(self.tempdir.name)[0])[0]
        name = os.path.basename(path)
        mime = mimetypes.guess_type(path)[0]

        if mime in IMAGE_TYPES and os.path.exists(path):
            # Don't delete the old image. It is also referenced in the HTML.
            # TODO: find replace all instances of the image in the book contents.
            # cover = self.get_cover()
            # os.remove(cover)

            id_num = self.get_all('cover')[0].attrib['content']
            element = self.etree.getroot().find(f"./opf:manifest/opf:item/[@id=\"{id_num}\"]",
                                                NAMESPACES)

            element.attrib['media-type'] = mime
            element.attrib['href'] = name

            shutil.copy(path, os.path.join(based, name))


    def set_identifier(self, name: str, scheme: str = None) -> None:
        """Sets the epub's identifier. This is generally the book's ISBN or a URI."""

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

        # Work around ElementTree issue: https://bugs.python.org/issue17088 (See comment in save)
        del element.attrib[f"{{{NAMESPACES['opf']}}}scheme"]
        element.attrib['opf:scheme'] = scheme


    def save(self, path: str, overwrite: bool = False) -> None:
        """Saves the opened EPub with the modified metadata to the file specified in `path`.
        If you want to overwrite an existing file set `overwrite=True`."""

        # Remove some characters that could cause file system errors
        # This is mostly useful if you rename a file to the book title etc.
        dirname, basename = os.path.split(path)

        for char in ILLEGAL_CHARS:
            basename.replace(char, '-')

        path = os.path.join(dirname, basename)

        if os.path.exists(path) and not overwrite:
            raise FileExistsError(f"{path} already exists. Use overwrite=True if you're serious.")

        self.add('date', time.strftime(TIME_FORMAT), {'event' : 'modified'})

        name = os.path.join(self.tempdir.name, find_opf_files(self.tempdir.name)[0])
        self.etree.write(name, xml_declaration=True, encoding='utf-8', method='xml')

        # Work around an old issue in ElementTree:
        # ElementTree incorrectly refuses to write attributes without namespaces
        # when default_namespace is used
        # https://bugs.python.org/issue17088
        # https://github.com/python/cpython/pull/11050

        with open(name, 'r') as f:
            text = f.read()
        
        text = text.replace('ns0:', '')
        text = text.replace(':ns0', ':opf')
        text = text.replace('<package ', '<package xmlns=\"http://www.idpf.org/2007/opf\" ')

        # TODO: Tidy XML before saving?
        # ElementTree has an indent function in Python 3.9, use that?
        with open(name, 'w') as opf:
            opf.write(text)

        with ZipFile(path, 'w', ZIP_DEFLATED) as zip_file:
            for root, _dirs, files in os.walk(self.tempdir.name):
                for name in files:
                    full_path = os.path.join(root, name)
                    zip_file.write(full_path, os.path.relpath(full_path, self.tempdir.name))
