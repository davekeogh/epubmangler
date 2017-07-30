OPF_NAMESPACE = '{http://www.idpf.org/2007/opf}'
DC_NAMESPACE = '{http://purl.org/dc/elements/1.1/}'

OPF_TEMPLATE = '''<?xml version='1.0' encoding='utf-8'?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="uuid_id" version="2.0">
    <metadata xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:opf="http://www.idpf.org/2007/opf"
        xmlns:dcterms="http://purl.org/dc/terms/"
        xmlns:calibre="http://calibre.kovidgoyal.net/2009/metadata"
        xmlns:dc="http://purl.org/dc/elements/1.1/">
    </metadata>
    <manifest>
    </manifest>
    <spine toc="ncx">
    </spine>
    <guide>
    </guide>
</package>'''

HTML_TEMPLATE = '''<html>
    <head>
        <style>
            p {{ font-size: 12px; }}
        </style>
    </head>
    <body>
        {description}
    </body>
</html>'''

ICON_NAME = 'gnome-books'

