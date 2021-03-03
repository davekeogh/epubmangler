"""A tool to edit the metadata of an epub file interactively"""
#!/usr/bin/env python

import os, os.path, sys

from typing import Dict, List, Tuple

import click

from epub import EPub, EPubMeta, is_epub


# Words to check for in various places
YES = ('y', 'Y', 'yes', 'YES', '') # Y/n means '' is yes
NO = ('n', 'N', 'no', 'NO')
QUIT = ('q', 'Q', 'quit', 'QUIT', 'exit', 'EXIT')


# Setup the commandline interface
@click.command(context_settings={'help_option_names' : ['--help', '-h']}) # Add -h to list

@click.option('-o', '--overwrite', is_flag=True, help='Overwrite OUTFILE even if it already exists')
@click.option('-v', '--verbose', is_flag=True, help='Print extra debug information')

@click.argument('INFILE', type=click.STRING)
@click.argument('OUTFILE', type=click.STRING, default='')

def command_line(infile: str, outfile: str, **options) -> None:
    """A tool to edit the metadata of an epub file interactively
    
    INFILE   the epub file to be edited

    OUTFILE  the path to save the modified file"""

    if not is_epub(infile):
        raise click.BadArgumentUsage(f"{infile} is not a valid epub file")

    if os.path.exists(outfile) and not options['overwrite']:
        raise click.BadArgumentUsage(f"{outfile} already exists, use --overwrite if you're sure")

    book = EPub(infile)
        
    while True:
        main_menu(book)
        # clear_screen()


def main_menu(book: EPub) -> None:
    """Prints the main menu and handles the user input"""

    click.echo(f"Editing {os.path.abspath(book.file)}...\n")
    
    count = 0
    selection = ''

    for meta in book.fields:
        print(f"[{count}] {meta}")
        count += 1
    
    print(f"[{count}] subjects: ", end='')
    for sub in book.subjects:
        print(sub.text, end=' ')
    count += 1
        
    print(f"\n[{count}] Quit")

    while not selection.isdigit() or int(selection) not in range(count + 1):
        selection = input(f"[0-{count}] : ")

        if selection in QUIT or (selection.isdigit() and int(selection) == count):
            quit(book)
    
    selection = int(selection)
    
    if selection == count - 1:
        edit_subjects(book.subjects)
    else:
        edit(book.fields[selection])


def edit(meta: EPubMeta) -> None:
    selection = ''
    new_text = ''
    new_attrib = {}

    print(f"\nEditing: {meta.tag} ...")
    print(f"[0] Text    : {meta.text}")
    print(f"[1] Attribs : {meta.attrib}")
    print(f"[2] Cancel")

    while not selection.isdigit() or int(selection) not in (0, 1, 2):
        selection = input(f"[0-2] : ")
    
    selection = int(selection)
    
    if selection == 0:
        new_text = input("[0] : ")
    elif selection == 1:
        new_attrib = input("[1] : ")


def edit_subjects(subjects: List[EPubMeta]) -> None:
    print(f"Editing subjects ...")


def confirm(text: str, attribs: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    """Asks the user if they're certain about the changes and allows them to make modifications if not"""
    ... # TODO


def quit(book: EPub) -> None:
    selection = ''

    while selection not in YES and selection not in NO:
        selection = input('[Y/n] Save? ')
    
    # TODO
    if selection in YES:
        print('Saving...')
        sys.exit(1)
    
    if selection in NO:
        print('Exiting...')
        sys.exit(1)


def clear_screen() -> None:
    """Clears the terminal screen in a crossplatform manner"""
    os.system('cls' if os.name == 'nt' else 'clear')
