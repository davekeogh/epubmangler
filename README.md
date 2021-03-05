# epubmangler

This module provides tools to modify the metadata of .epub format ebooks.

Documentation TBA. See `example.py` and `rename_epubs.py` for now.

Requires: Python 3.?

## Example usage

```python
from epubmangler import EPub

with EPub('Frankenstein.epub') as book: # https://gutenberg.org/ebooks/84

    # Get information about a book
    language = book.get('language')
    subjects = book.get_all('subject')

    # Modify existing elements
    book.set('title', 'Frankenstein 2')

    # Add and remove elements
    book.add('creator', 'David Keogh', {'opf:role' : 'adapter'})
    book.remove('date', {'opf:event' : 'conversion'})

    # Convenience functions
    book.set_cover('cat_picture.jpg')
    book.set_identifier('http://github.com/davekeogh/epubmangler', 'URI')

    # Add and remove subjects
    book.add_subject('Sequel')
    book.add_subject('Comedy')
    book.remove_subject('Horror tales')

    book.save('Frankenstein 2.epub', overwrite=True)
```
