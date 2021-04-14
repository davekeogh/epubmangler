"""Globals used by epubmangler"""

# Xpath queries for elements we will edit
# TODO: Make sure everything is on here
XPATHS = {
    'cover'         :   ['./opf:metadata/opf:meta/[@name="cover"]'],

    # The creator tag may have a "opf:file-as" attribute
    'creator'       :   ['./opf:metadata/dc:creator[@opf:role="aut"]',
                         './opf:metadata/dc:creator'],

    'title'         :   ['./opf:metadata/dc:title'],
    'description'   :   ['./opf:metadata/dc:description'],
    'subject'       :   ['./opf:metadata/dc:subject'],
    'publisher'     :   ['./opf:metadata/dc:publisher'],
    'language'      :   ['./opf:metadata/dc:language'],
    'rights'        :   ['./opf:metadata/dc:rights'],

    'date'          :   ['./opf:metadata/dc:date',
                         './opf:metadata/dc:date/[@opf:event="publication"]',
                         './opf:metadata/dc:date/[@opf:event="modification"]'],

    'id'            :   ['./opf:metadata/dc:identifier'],
    'isbn'          :   ['./opf:metadata/dc:identifier/[@opf:scheme="isbn"]',
                         './opf:metadata/dc:identifier/[@opf:scheme="ISBN"]'],
    'doi'           :   ['./opf:metadata/dc:identifier/[@opf:scheme="doi"]'
                         './opf:metadata/dc:identifier/[@opf:scheme="DOI"]'],
    'uuid'          :   ['./opf:metadata/dc:identifier/[@opf:scheme="uuid"]'
                         './opf:metadata/dc:identifier/[@opf:scheme="UUID"]'],
    'uri'           :   ['./opf:metadata/dc:identifier/[@opf:scheme="uri"]'
                         './opf:metadata/dc:identifier/[@opf:scheme="URI"]'],
    
    # This is not useful for much
    'meta'          :   ['./opf:metadata/opf:meta']
}

# These are all the XML namespaces that we should encounter
NAMESPACES = {
    'container' : 'urn:oasis:names:tc:opendocument:xmlns:container',
    'dc'        : 'http://purl.org/dc/elements/1.1/',
    'dcterms'   : 'http://purl.org/dc/terms/',
    'opf'       : 'http://www.idpf.org/2007/opf',
    'xsi'       : 'http://www.w3.org/2001/XMLSchema-instance',
    ''          : 'http://www.idpf.org/2007/opf'
}

# Only these types are valid as cover images
IMAGE_TYPES = ('image/jpeg', 'image/png', 'image/gif')

# Characters that may cause file system errors if used in filenames
ILLEGAL_CHARS = ('/', '\\', ':', '*', '?', '\"', '<', '>', '|')
