"""Functions used by epubmangler"""

from __future__ import annotations

import os
import json
import re

import xml.etree.ElementTree as ET

from pathlib import Path
from typing import Dict, List
from zipfile import ZipFile, is_zipfile, ZIP_DEFLATED

from .globals import ILLEGAL_CHARS, NAMESPACES


def file_as(name: str) -> str:
    """Returns a human's name with the surname first, or tries to at least.
    This may perform poorly with some names.

    `file_as('Mary Wollstonecraft Shelley')` returns `'Shelley, Mary Wollstonecraft'`"""

    parts = name.split()

    if not parts or len(parts) == 1:
        return name

    name = parts[0]

    for part in range(1, len(parts) - 1):
        name = f'{name} {parts[part]}'

    return f'{parts[len(parts) - 1]}, {name}'


def find_opf_files(path: str | bytes | os.PathLike) -> List[str]:
    """Returns a list of all the OPF files as defined in: `META-INF/container.xml`

    We only ever use the first one, and no books seem to have more than one, but
    the specification states that there could be."""

    with open(Path(path, 'META-INF/container.xml'), mode='r', encoding='utf-8') as container:
        xml_string = container.read()

    # Remove the default namespace definition (xmlns="http://some/namespace")
    # https://stackoverflow.com/questions/34009992/python-elementtree-default-namespace
    xml_string = re.sub(r'\sxmlns="[^"]+"', '', xml_string, count=1)

    root = ET.fromstring(xml_string)
    files = []

    for item in root.findall('./rootfiles/rootfile'):
        files.append(Path(path, item.attrib['full-path']))

    return files


def is_epub(path: str | bytes | os.PathLike) -> bool:
    """Returns True if `path` points to a valid epub file."""

    file_path = Path(path).absolute()

    if not file_path.exists() or file_path.suffix != '.epub' or not is_zipfile(file_path):
        return False

    with ZipFile(path, 'r', ZIP_DEFLATED) as zip_file:
        if 'mimetype' in zip_file.namelist():
            with zip_file.open('mimetype') as file_handle:
                return file_handle.read(20) == b'application/epub+zip'
        else:
            return False


def json_to_dict(input_str: str) -> Dict[str, str]:
    """A wrapper around `json.loads` that returns an empty dictionary rather than
    raising an exception."""

    try:
        return json.loads(input_str.replace("'", '"'))
    except json.decoder.JSONDecodeError:
        return {}  # TODO: Handle errors


def namespaced_text(text: str) -> str:
    """Returns the name and namespace formated for elementtree."""

    try:
        namespace, text = re.split(':', text)
    except ValueError:
        return text

    return f"{{{NAMESPACES[namespace]}}}{text}"


def new_element(name: str, text: str, attrib: Dict[str, str] = None) -> ET.Element:
    """Creates a new xml.etree.ElementTree.Element object and returns it."""

    return ET.Element(namespaced_text(f'dc:{name}'), text=text, attrib=attrib)


def sizeof_format(file: str) -> str:
    """Returns a human readable, decimal prefixed string containing the file size of `number`."""

    number = Path(file).stat().st_size

    for prefix in ('', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'):
        if number < 1000:
            return f'{number:.1f} {prefix}B'
        number /= 1000

    return f'{number:.1f} ?B'


def strip_namespace(text: str) -> str:
    """Strips the XML namespace from some text (either a tag or attribute name).
    This just returns the third element of `text.rpartition('}')`

    `'{http://purl.org/dc/elements/1.1/}creator'.rpartition('}')`

    returns `('{http://purl.org/dc/elements/1.1/', '}', 'creator')`

    Therefore, `text.rpartition('}')[2]`, will usually be the text without the namespace."""

    return text.rpartition('}')[2]


def strip_namespaces(attrib: Dict[str, str]) -> Dict[str, str]:
    """Strips the XML namespaces from all the keys in a dictionary.
    See `strip_namespace` for more information."""

    new_dict = {}

    if not attrib:
        return new_dict

    for key in attrib.keys():
        new_dict[strip_namespace(key)] = attrib[key]

    return new_dict


def strip_illegal_chars(path: str | bytes | os.PathLike, replace: str = '-') -> str:
    """Removes any characters from `path` that may cause file system errors with NTFS (Windows)."""

    file_path = Path(path)

    for character in ILLEGAL_CHARS:
        file_path.name.replace(character, replace)

    return file_path
