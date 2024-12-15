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
import pprint
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory as TempDir
from types import TracebackType
from typing import Dict, List, Self, Sequence, Type
from zipfile import ZIP_DEFLATED, ZipFile

from .functions import (
    find_opf_files,
    is_epub,
    namespaced_text,
    strip_illegal_chars,
    strip_namespace,
    strip_namespaces,
)
from .globals import IMAGE_TYPES, NAMESPACES, TIME_FORMAT, XPATHS


class EPubError(Exception):
    """Exception that is raised when an error occurs during an `EPub` method."""


class EPub:
    """A Python object representing an epub ebook's editable metadata."""

    def __init__(self, path: str | bytes | os.PathLike) -> Self:
        """Open an epub file and load its metadata into memory for editing."""

        self.etree: ET.ElementTree = None
        self.file: str = path
        self.metadata: List[ET.Element] = []
        self.modified: bool = False
        self.opf: str = None
        self.root: ET.Element = None
        self.tempdir: TempDir = None

        if not is_epub(path):
            raise EPubError(f"{self.file} is not a valid .epub file.")

        self.tempdir = TempDir(prefix='epubmangler-')  # pylint: disable=consider-using-with
        # TempDir.cleanup() is called in __del__()

        with ZipFile(self.file, 'r', ZIP_DEFLATED) as zip_file:
            zip_file.extractall(self.tempdir.name)

        self.parse_opf()

    def __del__(self) -> None:

        if self.tempdir:
            self.tempdir.cleanup()

    # The next two methods enable context manager support

    def __enter__(self) -> Self:

        return self

    def __exit__(self, _type: Type[BaseException] | None, _value: BaseException | None,
                 _traceback: TracebackType | None) -> bool:

        self.__del__()
        return False  # Raise any thrown exception before exiting

    # The next two methods make the object subscriptable like a Dict

    def __getitem__(self, name: str) -> ET.Element:

        return self.get(name)

    def __setitem__(self, name: str, text: str) -> None:

        try:
            self.get(name).text = text
        except EPubError:
            self.add(name, text)

    def __repr__(self) -> str:

        items = []

        for element in self.metadata:
            items.append({'tag': strip_namespace(element.tag),
                          'text': element.text if element.text else '',
                          'attrib': strip_namespaces(element.attrib)})

        return pprint.pformat(items)

    def add(self, name: str, text: str, attrib: Dict[str, str] = None) -> None:
        """Adds a new element to the metadata section of the tree."""

        try:
            for meta in self.get_all(name):
                if strip_namespaces(meta.attrib) == strip_namespaces(attrib):
                    raise EPubError(f"{Path(self.file).name} already has an \
                                    identical element. It is usually incorrect to have \
                                    more than one of most elements.")
        except NameError:
            pass

        element = ET.Element(namespaced_text(f'dc:{name}'))
        element.text = text
        if attrib:
            element.attrib = attrib

        self.etree.find('./opf:metadata', NAMESPACES).append(element)
        self.metadata = self.root.findall('./opf:metadata/*', NAMESPACES)
        self.modified = True

    def add_cover(self, path: str | bytes | os.PathLike) -> None:
        """Adds a cover element and the required additional metadata."""

        if self.has_element('cover'):
            raise EPubError(f"{Path(self.file).name} already has a cover. Use \
                            set_cover if you want to change it")

        mime = mimetypes.guess_type(path)[0]

        if mime not in IMAGE_TYPES or not Path(path).exists():
            raise EPubError(f"{Path(self.file).name} is not a valid image file.")

        filename = Path(Path(self.opf).parent, f'cover{Path(path).suffix}')
        shutil.copy(path, filename)

        metadata_element = ET.Element('meta')
        manifest_element = ET.Element('item')

        if self.root.attrib['version'] == '3.0':
            metadata_element.attrib = {'name': 'cover', 'content': 'cover-image'}
            manifest_element.attrib = {'id': 'cover-image', 'properties': 'cover-image',
                                       'href': filename.name, 'media-type': mime}
        else:
            metadata_element.attrib = {'name': 'cover', 'content': 'cover'}
            manifest_element.attrib = {'id': 'cover', 'href': filename.name,
                                       'media-type': mime}

        self.etree.find('./opf:metadata', NAMESPACES).append(metadata_element)
        self.etree.find('./opf:manifest', NAMESPACES).append(manifest_element)
        self.metadata = self.root.findall('./opf:metadata/*', NAMESPACES)
        self.modified = True

    def add_subject(self, name: str) -> None:
        """Adds a subject to the tree. This will do nothing if the subject already exists."""

        for subject in self.get_all('subject'):
            if subject.text == name:
                return

        element = ET.Element(namespaced_text('dc:subject'))
        element.text = name

        self.etree.find('./opf:metadata', NAMESPACES).append(element)
        self.metadata = self.root.findall('./opf:metadata/*', NAMESPACES)
        self.modified = True

    def get(self, name: str) -> ET.Element:
        """This will return the first matching element. Use get_all if you expect
        multiple elements to exist. There are usually several subject tags for instance."""

        element = None

        try:
            xpaths = XPATHS[name]
        except KeyError as key_error:
            raise EPubError(f"Unrecognized element: '{name}'") from key_error

        for xpath in xpaths:
            element = self.root.find(xpath, NAMESPACES)
            if element is not None:
                break

        if element is None:
            raise EPubError(f"{Path(self.file).name} has no element: '{name}'")

        return element

    def get_all(self, name: str) -> List[ET.Element]:
        """Returns a list of all the matching elements. There are often multiple date
        and subject tags for instance."""

        elements: List[ET.Element] = []

        try:
            xpaths = XPATHS[name]
        except KeyError as key_error:
            raise EPubError(f"Unrecognized element: '{name}'") from key_error

        for xpath in xpaths:
            # ET.Element can evaluate as False, so we need test that element is not None
            for e in self.root.findall(xpath, NAMESPACES):
                elements.append(e) if e is not None else ...
        
        return elements

    def get_cover(self) -> str:
        """Returns the full path of the cover image in the temporary directory.

        `./opf:manifest/opf:item/[@properties=\"cover-image\"]` contains the local path to the
        image in EPub version 3 files.

        We need to look at the attribs of two different tags to get the file name for EPub 2 files:

        `./opf:metadata/opf:meta/[@name="cover"]` gives us an element with an `content` attrib

        `./opf:manifest/opf:item/[@id=content]` gives us an element with a `href` element that
        points to the cover file."""

        based = Path(self.opf).parent

        def epub2() -> str:
            # Iterate over all <meta name="cover"> elements. Some ebooks that have had their cover
            # changed have an empty extra element.
            for item in self.get_all('cover'):
                element = item.attrib['content']

                if element is not None:
                    try:
                        name = self.root.find(f"./opf:manifest/opf:item/[@id=\"{element}\"]",
                                            NAMESPACES).attrib['href']
                        return Path(based, name)
                    except AttributeError:
                        pass

            return None

        if self.root.attrib['version'] == '3.0':
            try:
                name = self.root.find("./opf:manifest/opf:item/[@properties=\"cover-image\"]",
                                      NAMESPACES).attrib['href']
                return Path(based, name)
            except AttributeError: # Some books still define the cover the old way
                return epub2()

        else:
            return epub2()

    def has_element(self, name: str) -> bool:
        """Returns True if the EPub has a matching element. Otheriwse, returns False."""

        return bool(self.get(name))

    def remove(self, name: str, attrib: Dict[str, str] = None) -> None:
        """Removes an element from the tree. Books can have more than one date or creator element.
        Use `attrib` to get extra precision in these cases."""

        elements = self.get_all(name)

        if elements:
            if attrib:
                for element in elements:
                    if attrib == strip_namespaces(element.attrib):
                        self.root.find('./opf:metadata', NAMESPACES).remove(element)

            else:
                self.root.find('./opf:metadata', NAMESPACES).remove(elements[0])

            self.metadata = self.root.findall('./opf:metadata/*', NAMESPACES)
            self.modified = True

    def remove_subject(self, name: str) -> None:
        """Removes a subject element from the tree."""

        for subject in self.get_all('subject'):
            if subject.text == name:
                self.root.find('./opf:metadata', NAMESPACES).remove(subject)

        self.metadata = self.root.findall('./opf:metadata/*', NAMESPACES)
        self.modified = True

    def set(self, name: str, text: str, attrib: Dict[str, str] = None) -> None:
        """Sets the text and attributes of an existing element."""

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

        self.metadata = self.root.findall('./opf:metadata/*', NAMESPACES)
        self.modified = True

    def set_cover(self, path: str | bytes | os.PathLike) -> None:
        """Replaces the cover image of the book with `path`, provided it is valid image file."""

        mime = mimetypes.guess_type(path)[0]
        cover = self.get_cover()

        if mime in IMAGE_TYPES and Path(path).exists() and cover:
            os.remove(cover)
            shutil.copy(path, cover)

        self.metadata = self.root.findall('./opf:metadata/*', NAMESPACES)
        self.modified = True

    def set_identifier(self, name: str, scheme: str | None) -> None:
        """Sets the epub's identifier. This is generally the book's ISBN or a URI."""

        id_num = self.root.attrib['unique-identifier']
        element = self.root.find(f"./opf:metadata/dc:identifier/[@id=\"{id_num}\"]", NAMESPACES)
        element.text = name

        if not scheme:
            if name.startswith('http'):
                scheme = 'URI'
            elif name.startswith('doi:'):
                scheme = 'DOI'
            else:
                scheme = 'ISBN'

        # Work around ElementTree issue: https://bugs.python.org/issue17088
        # See comment in save for details
        key = f"{{{NAMESPACES['opf']}}}scheme"
        if key in element.attrib:
            del element.attrib[key]

        element.attrib['opf:scheme'] = scheme

        self.metadata = self.root.findall('./opf:metadata/*', NAMESPACES)
        self.modified = True

    def extend(self, metadata: Sequence[ET.Element]) -> None:
        """Extends the current metadata by appending elements from `metadata`."""

        self.root.find('./opf:metadata', NAMESPACES).extend(metadata)
        self.metadata.extend(metadata)
        self.modified = True

    def update(self, metadata: Sequence[ET.Element]) -> None:
        """Replace the entirety of the metadata section of the tree with `metadata`."""

        self.root.find('./opf:metadata', NAMESPACES).clear()
        self.extend(metadata)

    def parse_opf(self, modified: bool = False) -> None:
        """Loads the opf file into memory. This is used on initialization, and may be of use
        if the file is edited from another process."""

        try:
            self.opf = find_opf_files(self.tempdir.name)[0]
        except IndexError as index_error:  # No OPF found
            raise EPubError(f"{self.file} is not a valid .epub file.") from index_error

        try:
            self.etree = ET.parse(self.opf)
        except ET.ParseError as parse_error:  # XML error
            raise EPubError(f"{self.file} is not a valid .epub file.") from parse_error

        self.root = self.etree.getroot()
        self.metadata = self.root.findall('./opf:metadata/*', NAMESPACES)
        self.modified = modified

    def save(self, path: str | bytes | os.PathLike, overwrite: bool = False) -> None:
        """Saves the opened EPub with the modified metadata to the file specified in `path`.
        If you want to overwrite an existing file set `overwrite=True`."""

        path = Path(strip_illegal_chars(path))

        if path.exists() and not overwrite:
            raise FileExistsError(f"{path} already exists. Use overwrite=True if you're serious.")

        self.add('date', time.strftime(TIME_FORMAT), {'event': 'modified'})

        try:  # Tidy the XML (added in Python 3.9)
            ET.indent(self.etree)
        except AttributeError:
            pass

        self.etree.write(path, xml_declaration=True, encoding='utf-8', method='xml')

        # Work around an old issue in ElementTree:
        # ElementTree incorrectly refuses to write attributes without namespaces
        # when default_namespace is used
        # https://bugs.python.org/issue17088
        # https://github.com/python/cpython/pull/11050

        with open(self.opf, mode='r', encoding='utf-8') as opf:
            text = opf.read()

        text = text.replace('ns0:', '')
        text = text.replace(':ns0', ':opf')
        text = text.replace('<package ', '<package xmlns=\"http://www.idpf.org/2007/opf\" ')

        with open(self.opf, mode='w', encoding='utf-8') as opf:
            opf.write(text)

        with ZipFile(path, 'w', ZIP_DEFLATED) as zip_file:
            for root, _dirs, files in os.walk(self.tempdir.name):
                for name in files:
                    full_path = Path(root, name)
                    zip_file.write(full_path, full_path.relative_to(self.tempdir.name))

        self.modified = False
