# epubmangler

Tools to read and modify the metadata of EPUB files.

Documentation to be written. See the minimal example below and others in the `example` directory.

Requires: Python 3.8

## Example usage

```python
from epubmangler import EPub

with EPub('Frankenstein.epub') as book:  # https://gutenberg.org/ebooks/84

    # Get information about a book
    language = book.get('language')
    subjects = book.get_all('subject')
    book.pretty_print()

    # Modify existing elements
    book.set('title', 'Frankenstein 2')
    book.set_cover('cat_picture.jpg')
    book.set_identifier('http://github.com/davekeogh/epubmangler', 'URI')

    # Add and remove elements
    book.add('contributor', 'epubmangler', {'opf:role' : 'bkp'})
    book.remove('date', {'opf:event' : 'conversion'})

    # Add and remove subjects
    book.add_subject('Sequel')
    book.add_subject('Comedy')
    book.remove_subject('Horror tales')

    book.save('Frankenstein 2.epub', overwrite=True)

```
