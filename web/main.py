"""A simple web application using epubmangler"""

import os
import shutil
import uuid

from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from epubmangler import EPub, strip_namespace


class TemplateResponse(HTMLResponse):
    template:str = open(Path('static/template.html'), 'r').read()
    def __init__(self, inner_html: str) -> None:
        HTMLResponse.__init__(self, self.template.replace('{{body}}', inner_html))


app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/upload', StaticFiles(directory='upload'), name='upload')

@app.get("/")
async def main():
    return HTMLResponse(open(Path('static/main.html'), 'r').read())


@app.post('/edit')
async def edit(file: UploadFile = File(...)):
    filename = Path("upload", file.filename)

    with open(filename, 'wb') as temp:
        temp.write(await file.read())

    try:
        epub = EPub(filename)
    except ValueError:
        os.remove(filename)
        return TemplateResponse(f'not an epub: {filename}')

    inner_html = ''

    if epub.get_cover():
        cover_path = Path(epub.get_cover())
        temp_cover = Path()
        inner_html += '<div id="content">'

        if cover_path.is_file():
            temp_cover = Path('upload/image', f'{uuid.uuid4()}{cover_path.suffix}')
            shutil.copy(cover_path, temp_cover)

        if temp_cover.is_file():
            inner_html += f'<img src="{temp_cover}" alt="cover image" />\n'

    inner_html += (
        f'<p>editing: {filename.name}</p>\n'
        '<form action="/download" method="POST">\n'
        f'<input type="hidden" name="filename" value="{filename}" />\n'
    )

    for item in epub.metadata:
        if strip_namespace(item.tag) == 'description':
            inner_html += (
                f'<label for="{item.tag}">{strip_namespace(item.tag)}:</label><br />'
                f'<textarea rows="5" cols="50" name="{item.tag}-text">{item.text}</textarea>'
            )
        else:
            inner_html += (
                f'<label for="{item.tag}">{strip_namespace(item.tag)}:</label>'
                f'<input type="text" name="{item.tag}-text" value="{item.text}" />'
            )


        if item.attrib:
            inner_html += f'<input type="text" name="{item.tag}-attrib" value="{item.attrib}" />'

        inner_html += f'<button type="button" class="delete">x</button><br />\n'

    inner_html += (
        '<p><label for="new-tag">new:</label><br />'
        '<input type="text" name="new-tag" /><input type="text" name="new-text" />'
        '<input type="text" name="new-attrib" />'
        '<button type="button" class="add">+</button></p>\n'
        '<button type="submit">Save</button>\n'
        '</form></div>'
    )

    return TemplateResponse(inner_html)


@app.post("/download")
async def download(request: Request):
    form = await request.form()

    print(str(form))

    # TODO: The form data needs to have the -tag, -text, -attrib suffixes stripped etc.

    if Path(form['filename']).parent != Path('upload'):
        return TemplateResponse(f'bad request: {form["filename"]}')

    epub = EPub(Path(form['filename']))

    return TemplateResponse(f'downloading: {Path(epub.file).name}')
