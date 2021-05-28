"""A simple web application using epubmangler"""

import json
import os
import shutil
import uuid

from pathlib import Path
from xml.etree.ElementTree import Element

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from epubmangler import EPub, strip_namespace


class TemplateResponse(HTMLResponse):
    template:str = open(Path('static/template.html'), 'r').read()
    def __init__(self, inner_html: str) -> None:
        HTMLResponse.__init__(self, self.template.replace('{{body}}', inner_html))


app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/upload', StaticFiles(directory='upload'), name='upload')


@app.get('/', response_class=HTMLResponse)
async def main():
    return HTMLResponse(open(Path('static/main.html'), 'r').read())


@app.post('/edit', response_class=HTMLResponse)
async def edit(file: UploadFile = File(...)):
    filename = Path("upload", file.filename)

    with open(filename, 'wb') as temp:
        temp.write(await file.read())

    try:
        epub = EPub(filename)
    except ValueError:
        os.remove(filename)
        return TemplateResponse(f'not an epub: {filename}')

    inner_html = '<div id="content">\n'

    if epub.get_cover():
        cover_path = Path(epub.get_cover())
        temp_cover = Path()

        if cover_path.is_file():
            temp_cover = Path('upload/image', f'{uuid.uuid4()}{cover_path.suffix}')
            shutil.copy(cover_path, temp_cover)

        if temp_cover.is_file():
            alt_text = f'{epub["title"].text} by {epub["creator"].text}'
            inner_html += f'<img src="{temp_cover}" id="cover" alt="Cover page of {alt_text}" />\n'

    inner_html += (
        f'<h1>Editing: {filename.name}</h1>\n'
        "<p>Pro tip: Don't touch the <em>Attrib</em> column, unless you know what you are doing.</p>"
        '<form action="/download" method="POST">'
        f'<input type="hidden" name="filename" value="{filename}" />\n'
        '<table><tr><th>Tag</th><th>Text</th><th>Attrib</th><th class="blank"></th></tr>\n'
    )

    for item in epub.metadata:
        inner_html += f'<tr><td><input type="hidden" name="{item.tag}" />\n'

        if strip_namespace(item.tag) == 'description':
            inner_html += (
                f'{strip_namespace(item.tag)}</td>'
                f'<td><textarea rows="5" cols="50" name="{item.tag}-text">{item.text}</textarea></td>'
            )
        else:
            inner_html += (
                f'{strip_namespace(item.tag)}:</td>'
                f'<td><input type="text" name="{item.tag}-text" value="{item.text}" /></td>'
            )


        if item.attrib:
            inner_html += f'<td><input type="text" name="{item.tag}-attrib" value="{item.attrib}" /></td>'
        else:
            inner_html += f'<td><input type="text" name="{item.tag}-attrib" /></td>'

        inner_html += f'<td class="blank"><button type="button" name="{item.tag}-del">x</button></td></tr>\n'

    inner_html += (
        '<tr><td><input type="text" name="new-tag" /></td>'
        '<td><input type="text" name="new-text" /></td>'
        '<td><input type="text" name="new-attrib" /></td>'
        '<td class="blank"><button type="button" name="new-button">+</button></td></tr>\n'
        '</table><br /><button type="submit">Save</button>'
        '</form>\n</div>'
    )

    return TemplateResponse(inner_html)


@app.post('/download', response_class=FileResponse)
async def download(request: Request):
    form = await request.form()

    if Path(form['filename']).parent != Path('upload'):
        return TemplateResponse(f'bad request: {form["filename"]}')

    items: Element = []

    for k in form.keys():
        if k.startswith('new-'):
            continue
        if k.endswith('-text'):
            continue
        if k.endswith('-attrib'):
            continue
        if k == "filename":
            continue

        items.append(Element(k))

    for element in items:
        element.text = form[f'{element.tag}-text']

        if not form[f'{element.tag}-attrib']:
            continue

        try:
            element.attrib = json.loads(form[f'{element.tag}-attrib'].replace("'", '"'))
        except json.decoder.JSONDecodeError:
            # TODO: Handle errors
            continue

    epub = EPub(Path(form['filename']))
    epub.update(items)
    epub.save(Path(form['filename']), overwrite=True)

    return FileResponse(Path(form['filename']), filename=Path(form['filename']).name)

    #return TemplateResponse(f'Downloading: {Path(epub.file).name}...')
