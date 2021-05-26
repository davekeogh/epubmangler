"""A simple web application using epubmangler"""

import os
import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from epubmangler import EPub, strip_namespace

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
template = open(Path("static/template.html"), "r").read()

# TODO: Needs a backend to delete everything in /upload after a while


@app.get("/")
async def main():
    return HTMLResponse(open(Path("static/main.html"), "r").read())


@app.post("/edit")
async def edit(file: UploadFile = File(...)):
    filename = Path("upload", file.filename)

    with open(filename, "wb") as temp:
        temp.write(await file.read())

    try:
        epub = EPub(filename)
    except ValueError:
        os.remove(filename)
        return HTMLResponse(template.replace("{{ body }}", f"not an epub: {filename}"))

    cover_path = Path(epub.get_cover())
    temp_cover = None

    if cover_path.is_file():
        temp_cover = Path('static', f'{hash(str(cover_path))}.{cover_path.suffix}')
        shutil.copy(cover_path, temp_cover)

    inner_html = (
        f'<p>editing: {epub.file}</p>\n'
        '<form action="/download" method="POST">\n'
        f'<input type="hidden" name="filename" value="{filename}" />\n'
    )

    for item in epub.metadata:
        inner_html += (
            f'<label for="{item.tag}">{strip_namespace(item.tag)}:</label>'
            f'<input type="text" name="{item.tag}-text" value="{item.text}" />'
        )

        if item.attrib:
            inner_html += f'<input type="text" name="{item.tag}-attrib" value="{item.attrib}" />'

        inner_html += f'<button type="button" class="delete">x</button><br />\n'

    inner_html += (
        '<label for="new-tag">new:</label><input type="text" name="new-tag" />'
        '<input type="text" name="new-text" /><input type="text" name="new-attrib" />'
        '<button type="button" class="add">+</button><br /><br />\n'
        '<button type="submit">Save</button>\n'
        '</form>'
    )

    return HTMLResponse(template.replace("{{ body }}", inner_html))


@app.post("/download")
async def download(filename: str = Form(...)):
    if Path(filename).parent != Path("upload"):
        return HTMLResponse(template.replace("{{ body }}", f"bad request: {filename}"))

    inner_html = f"downloading: {filename}"

    return HTMLResponse(template.replace("{{ body }}", inner_html))
