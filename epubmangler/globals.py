"""Globals used by epubmangler"""

VERSION = '0.1.0'

# Xpath queries for elements we will edit
XPATHS = {
    # http://idpf.org/epub/20/spec/OPF_2.0_final_spec.html
    'creator'       :   ['./opf:metadata/dc:creator[@opf:role="aut"]',
                         './opf:metadata/dc:creator'],
    'title'         :   ['./opf:metadata/dc:title'],
    'description'   :   ['./opf:metadata/dc:description'],
    'subject'       :   ['./opf:metadata/dc:subject'],
    'publisher'     :   ['./opf:metadata/dc:publisher'],
    'language'      :   ['./opf:metadata/dc:language'],
    'rights'        :   ['./opf:metadata/dc:rights'],
    'contributor'   :   ['./opf:metadata/dc:contributor'],
    'type'          :   ['./opf:metadata/dc:type'],
    'format'        :   ['./opf:metadata/dc:format'],
    'source'        :   ['./opf:metadata/dc:source'],
    'relation'      :   ['./opf:metadata/dc:relation'],
    'coverage'      :   ['./opf:metadata/dc:coverage'],
    
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
    
    'cover'         :   ['./opf:metadata/opf:meta/[@name="cover"]'],
    'meta'          :   ['./opf:metadata/opf:meta'] # Anything else
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

# time.strftime(TIME_FORMAT)
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
