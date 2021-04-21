# epubmangler

Tools to modify the metadata of EPUB files

Documentation TBA. See `example/rename_epubs.py` and `gtk/edit.py` for now.

Requires: Python 3.7

## Example usage

```python
import time
from epubmangler import EPub

with EPub('Frankenstein.epub') as book: # https://gutenberg.org/ebooks/84

    # Get information about a book
    language = book.get('language')
    subjects = book.get_all('subject')

    # Modify existing elements
    book.set('title', 'Frankenstein 2')
    book.set_cover('cat_picture.jpg')
    book.set_identifier('http://github.com/davekeogh/epubmangler', 'URI')

    # Add and remove elements
    book.add('contributor', 'epubmangler', {'opf:role' : 'bkp'})
    book.remove('date', {'opf:event' : 'conversion'})
    book.add('date', time.strftime('%F'), {'opf:event' : 'conversion'})

    # Add and remove subjects
    book.add_subject('Sequel')
    book.add_subject('Comedy')
    book.remove_subject('Horror tales')

    book.save('Frankenstein 2.epub', overwrite=True)

```
