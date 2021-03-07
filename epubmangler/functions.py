"""Useful functions used by epubmangler"""

from __future__ import annotations

import os
import re

import xml.etree.ElementTree as ET

from typing import Dict, List
from zipfile import ZipFile, is_zipfile, ZIP_DEFLATED


def file_as(name: str) -> str:
    """Returns a human's name with the surname first, or tries to at least.
    This may perform poorly with some names.
    
    `file_as('Mary Wollstonecraft Shelley')` returns `'Shelley, Mary Wollstonecraft'`"""
    
    parts = name.split()
    name = parts[0]
    
    if len(parts) == 1:
        return parts[0]   

    for part in range(1, len(parts) - 1):
        name = f'{name} {parts[part]}'

    return f'{parts[len(parts) - 1]}, {name}'


def find_opf_files(path: str) -> List[str]:
    """Returns a list of all the OPF files as defined in: `META-INF/container.xml`

    We only ever use the first one, and no books seem to have more than one, but
    the specification states that there could be."""

    with open(os.path.join(path, 'META-INF/container.xml')) as container:
        xmlstring = container.read()

    # Remove the default namespace definition (xmlns="http://some/namespace")
    # https://stackoverflow.com/questions/34009992/python-elementtree-default-namespace
    xmlstring = re.sub(r'\sxmlns="[^"]+"', '', xmlstring, count=1)

    root = ET.fromstring(xmlstring)
    files = []

    for item in root.findall('./rootfiles/rootfile'):
        files.append(os.path.join(path, item.attrib['full-path']))

    return files


def is_epub(path: str) -> bool:
    """Returns True if `path` points to a valid epub file."""

    if not os.path.exists(path):
        return False

    if os.path.splitext(path)[1] != '.epub':
        return False

    if not is_zipfile(path):
        return False

    with ZipFile(path, 'r', ZIP_DEFLATED) as zip_file:
        if 'mimetype' in zip_file.namelist():
            with zip_file.open('mimetype') as file_handle:
                return file_handle.read(20) == b'application/epub+zip'
        else:
            return False


def namespaced_text(namespace:str, text:str) -> str:
    """Returns the name and namespace formated for elementtree."""

    return f"{{{namespace}}}{text}"


def strip_namespace(text: str) -> str:
    """Strips the XML namespace from some text (either a tag or attribute name).
    This just returns the third element of `text.rpartition('}')`

    `'{http://purl.org/dc/elements/1.1/}creator'.rpartition('}')`
    returns `('{http://purl.org/dc/elements/1.1/', '}', 'creator')`

    Therefore, `text.rpartition('}')[2]`, will usually be the text without the namespace."""

    return text.rpartition('}')[2]


def strip_namespaces(attrib: Dict[str, str]) -> Dict[str, str]:
    """Strips the XML namespaces from all the keys in a dictionary.
    See strip_namespace for more information."""

    new_dict = {}

    for key in attrib.keys():
        new_dict[strip_namespace(key)] = attrib[key]

    return new_dict
