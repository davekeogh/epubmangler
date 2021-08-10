"""A simple web application using epubmangler"""

import os
import re
import shutil
import time
import uuid

import uvicorn

from multiprocessing import Process
from pathlib import Path
from xml.etree.ElementTree import Element

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from epubmangler import EPub, EPubError, json_to_dict, strip_namespace

INFO, WARNING, ERROR = 0, 1, 2
UPLOAD = Path('upload')
STATIC = Path('static')


def log(message: str, level: int = INFO, pid: int = None):
    """Prints a message that looks kind of like the ones made by uvicorn."""

    if level == INFO:
        message = f'\u001b[32mINFO\u001b[0m:     {message}'
    elif level == WARNING:
        message = f'\u001b[33mWARNING\u001b[0m:     {message}'
    elif level == ERROR:
        message = f'\u001b[31mERROR\u001b[0m:     {message}'

    if pid:
        message += ' [\u001b[36m' + str(p.pid) + '\u001b[0m]'

    print(message)


def tidy(sleep_length: int = 600):
    """Remove all files in the upload directory on a regular basis.
    
    `sleep_length` is the number of seconds to sleep after each iteration."""

    while True:
        for file in os.listdir(UPLOAD):
            if file != 'image' and os.stat(Path(UPLOAD, file)).st_mtime > sleep_length:
                os.remove(Path(UPLOAD, file))

        for file in os.listdir(Path(UPLOAD, 'image')):
            if os.stat(Path(UPLOAD, 'image', file)).st_mtime > sleep_length:
                os.remove(Path(UPLOAD, 'image', file))

        try:
            time.sleep(sleep_length)
        except KeyboardInterrupt:
            break


class TemplateResponse(HTMLResponse):
    template:str = open(Path(STATIC, 'template.html'), 'r').read()
    def __init__(self, html: str) -> None:
        HTMLResponse.__init__(self, self.template.replace('{{body}}', html))


app = FastAPI()
app.mount('/static', StaticFiles(directory=STATIC), name='static')
app.mount('/upload', StaticFiles(directory=UPLOAD), name='upload')


@app.get('/', response_class=HTMLResponse)
async def main():
    return HTMLResponse(open(Path(STATIC, 'main.html'), 'r').read())


@app.post('/edit', response_class=HTMLResponse)
async def edit(file: UploadFile = File(...)):
    filename = UPLOAD / file.filename

    with open(filename, 'wb') as temp:
        temp.write(await file.read())

    try:
        epub = EPub(filename)
    except ValueError:
        os.remove(filename)
        return TemplateResponse(f'not an epub: {filename}')

    html = (
        '<div id="content">\n'
        f'<h1>Editing: {filename.name}</h1>\n'
        "<p>Pro tip: Don't touch the <em>Attrib</em> column, unless you know what you are doing.</p>"
        '<form action="/download" method="post">'
        f'<input type="hidden" name="filename" value="{filename}" />\n'
    )

    if epub.get_cover():
        cover_path = Path(epub.get_cover())
        temp_cover = Path()

        if cover_path.is_file():
            temp_cover = UPLOAD / 'image' / f'{uuid.uuid4()}{cover_path.suffix}'
            shutil.copy(cover_path, temp_cover)

        if temp_cover.is_file():
            html += f'<input type="file" id="cover-upload" name="cover-upload" accept="image/*" />'

            alt_text = f'Cover page of {epub["title"].text} by {epub["creator"].text}'
            html += f'<img src="{temp_cover}" id="cover" alt="{alt_text}" />\n'

    html += '<table><tr><th>Tag</th><th>Text</th><th>Attrib</th><th class="blank"></th></tr>\n'

    for item in epub.metadata:
        html += f'<tr><td><input type="hidden" name="{item.tag}" />\n'

        if strip_namespace(item.tag) == 'description':
            html += (
                f'{strip_namespace(item.tag)}</td>'
                f'<td><textarea rows="5" cols="50" name="{item.tag}-text">{item.text}</textarea></td>'
            )
        else:
            html += (
                f'{strip_namespace(item.tag)}:</td>'
                f'<td><input type="text" name="{item.tag}-text" value="{item.text}" /></td>'
            )

        if item.attrib:
            html += f'<td><input type="text" name="{item.tag}-attrib" value="{str(item.attrib)}" /></td>'
        else:
            html += f'<td><input type="text" name="{item.tag}-attrib" /></td>'

        html += f'<td class="blank"><button type="button" name="{item.tag}-del">x</button></td></tr>\n'

    html += (
        '<tr><td><input type="text" name="new-tag" /></td>'
        '<td><input type="text" name="new-text" /></td>'
        '<td><input type="text" name="new-attrib" /></td>'
        '<td class="blank"><button type="button" name="new-button">+</button></td></tr>\n'
        '</table><br /><button type="submit">Save</button></form>\n</div>'
    )

    return TemplateResponse(html)


@app.post('/download', response_class=FileResponse)
async def download(request: Request):
    form = await request.form()
    filename = Path(form['filename'])

    if filename.parent != UPLOAD:
        return TemplateResponse(f'bad request: {form}')

    epub = EPub(form['filename'])
    items = []
    new_items = []

    for field in form.keys():
        if field.endswith('-text') or field.endswith('-attrib') or field == 'filename':
            continue  # TODO: Refactor to use match in 3.10+
        elif field == 'cover-upload':
            try:
                epub.set_cover(form['cover-upload'])
            except EPubError:
                epub.add_cover(form['cover-upload'])
        elif re.match('(new[0-9]*)-(.+)', field):
            new_items.append(Element(field))
        else:
            items.append(Element(field))

    for element in items:
        element.text = form[f'{element.tag}-text']
        element.attrib = json_to_dict(form[f'{element.tag}-attrib'])

    for element in new_items:
        prefix, element.tag = re.match('(new[0-9]*)-(.+)', element.tag).groups()
        element.text = form[f'{prefix}-text']
        element.attrib = json_to_dict(form[f'{prefix}-attrib'])

    epub.update(items)
    epub.save(filename, overwrite=True)

    # return TemplateResponse(f'Downloading: {Path(epub.file).name}...')
    return FileResponse(filename, filename=filename.name)


if __name__ == '__main__':
    p = Process(target=tidy)
    p.start()
    log('Started tidy process', level=INFO, pid=p.pid)
    uvicorn.run(app, host='127.0.0.1', port=8000)
    log('Finished tidy process', level=INFO, pid=p.pid)