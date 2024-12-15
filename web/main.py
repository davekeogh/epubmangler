"""A simple web application using fastapi and epubmangler."""

import enum
import os
import re
import shutil
import sys
import time
import uuid

import xml.etree.ElementTree as ET

from multiprocessing import Process
from pathlib import Path
from typing import Optional, Self, Sequence, TextIO

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

import uvicorn

from epubmangler import EPub, EPubError, json_to_dict, strip_namespace


ROOT = Path("/home/david/Projects/epubmangler/web")
UPLOAD = ROOT / "upload"
IMAGES = UPLOAD / "image"
STATIC = ROOT / "static"
INDEX = STATIC / "main.html"
TEMPLATE = open(STATIC / "template.html", mode="r", encoding="utf-8").read()


class ERROR_LEVEL(enum.IntEnum):
    INFO = 0
    WARNING = 1
    ERROR = 2


class TemplateResponse(HTMLResponse):
    """A template wrapper around FastAPI's HTMLResponse.

    `html` is string representing the body of the final webpage's HTML."""

    def __init__(self, html: str) -> Self:
        HTMLResponse.__init__(self, TEMPLATE.replace("{{body}}", html))


def log(
    message: str, level: int = 0,
    pid: int = 0, file: Optional[TextIO] = sys.stdout) -> None:
    """Prints a message that looks kind of like the ones made by uvicorn.

    `level` is an `ERROR_LEVEL` or defaults to `INFO`

    `file` can be set to a file-like object or defaults to stdout."""

    final_message = ""

    match level:
        case ERROR_LEVEL.WARNING:
            final_message += f"\u001b[33m{level.name}\u001b[0m:     {message}"
        case ERROR_LEVEL.ERROR:
            final_message += f"\u001b[31m{level.name}\u001b[0m:     {message}"
        case ERROR_LEVEL.INFO | _:
            final_message += f"\u001b[32m{level.name}\u001b[0m:     {message}"

    if pid:
        final_message += f" [\u001b[36m{pid}\u001b[0m]"

    print(final_message, file=file)


def tidy(
    directories: Sequence[os.PathLike[str]],
    life_time: int = 600,
    sleep_length: int = 300,
) -> None:
    """Remove all files in a group of directories on a regular basis.

    `directories` the list of directories to monitor

    `life_time` the number of seconds to retain files

    `sleep_length` the number of seconds to sleep after each iteration"""

    while True:
        for dir in directories:
            for file in os.listdir(dir):
                path = Path(dir, file)
                if path.is_dir():
                    continue
                if path.stat().st_mtime > life_time:
                    os.remove(path)

        time.sleep(sleep_length)


# Set up our FastAPI application
app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.mount("/upload", StaticFiles(directory=UPLOAD), name="upload")


@app.get("/", response_class=HTMLResponse)
async def main() -> HTMLResponse:
    """Returns the static html entry point of our application."""
    return HTMLResponse(open(INDEX, mode="r", encoding="utf-8").read())


@app.post("/edit", response_class=TemplateResponse)
async def edit(file: UploadFile = File(...)) -> TemplateResponse:
    """The edit page of our application."""

    filename = Path(UPLOAD / file.filename)

    with open(filename, "wb") as temp:
        temp.write(await file.read())

    try:
        epub = EPub(filename)
    except EPubError:
        os.remove(filename)
        return TemplateResponse(
            f"""<p>Not a valid epub file: {filename.name}\n\n
            Create an issue at 
            <a href="https://github.com/davekeogh/epubmangler/issues">
            https://github.com/davekeogh/epubmangler/issues</a> 
            if your epub is not supported properly. Sorry!</p>"""
        )

    html = f"""<form action="/download" method="post">
        <input type="hidden" name="filename" value="{filename}" />"""

    cover_path = Path(epub.get_cover())

    if cover_path:
        temp_cover = Path()

        if cover_path.is_file():
            temp_cover = UPLOAD / "image" / f"{uuid.uuid4()}{cover_path.suffix}"
            shutil.copy(cover_path, temp_cover)

        if temp_cover.is_file():
            html += '<input type="file" id="cover-upload" name="cover-upload" accept="image/*" />'

            alt_text = f'Cover page of {epub["title"].text} by {epub["creator"].text}'
            html += f'<img src="{temp_cover.relative_to(ROOT)}" id="cover" alt="{alt_text}" />'

    html += f"""<h1>Editing: {filename.name}</h1>
            <p>Pro tip: Don't touch the <em>Attrib</em> column, unless you know what you are doing.</p>
            <table><tr><th>Tag</th><th>Text</th><th>Attrib</th><th class="blank"></th></tr>"""

    for item in epub.metadata:
        html += f'<tr><td><input type="hidden" name="{item.tag}" />'

        if strip_namespace(item.tag) == "description":
            html += f"""{strip_namespace(item.tag)}</td>
                <td><textarea rows="5" cols="50" name="{item.tag}-text">
                {item.text}</textarea></td>"""
        else:
            html += f"""{strip_namespace(item.tag)}:</td>
                <td><input type="text" name="{item.tag}-text" value="{item.text}" /></td>"""

        if item.attrib:
            html += f"""<td><input type="text" name="{item.tag}-attrib"
                value="{str(item.attrib)}" /></td>"""
        else:
            html += f'<td><input type="text" name="{item.tag}-attrib" /></td>'

        html += f'<td class="blank"><button type="button" name="{item.tag}-del">x</button></td></tr>'

    html += """<tr><td><input type="text" name="new-tag" /></td>
            <td><input type="text" name="new-text" /></td>
            <td><input type="text" name="new-attrib" /></td>
            <td class="blank"><button type="button" name="new-button">+</button></td></tr>
            </table><br /><button type="submit">Save</button></form>"""

    return TemplateResponse(html)


@app.post("/download", response_class=FileResponse)
async def download(request: Request) -> FileResponse:  # TemplateResponse
    """Download the edited epub."""

    form = await request.form()
    filename = Path(form["filename"])

    if not filename or filename.parent != UPLOAD:
        return TemplateResponse(f"bad request: {form}")

    epub = EPub(form["filename"])
    items = []
    new_items = []

    for field in form.keys():
        if field.endswith("-text") or field.endswith("-attrib") or field == "filename":
            continue
        if field == "cover-upload":
            try:
                epub.set_cover(form["cover-upload"])
            except EPubError:
                epub.add_cover(form["cover-upload"])
        if re.match("(new[0-9]*)-(.+)", field):
            new_items.append(ET.Element(field))

    for element in items:
        element.text = form[f"{element.tag}-text"]
        element.attrib = json_to_dict(form[f"{element.tag}-attrib"])

    for element in new_items:
        prefix, element.tag = re.match("(new[0-9]*)-(.+)", element.tag).groups()
        element.text = form[f"{prefix}-text"]
        element.attrib = json_to_dict(form[f"{prefix}-attrib"])

    items += new_items

    epub.update(items)
    epub.save(filename, overwrite=True)

    # return TemplateResponse(f'Downloading: {Path(epub.file).name}...')
    return FileResponse(filename, filename=filename.name)


if __name__ == "__main__":
    p = Process(target=tidy, args=((UPLOAD, IMAGES), 600, 300))
    p.start()
    log("Started tidy process", level=ERROR_LEVEL.INFO, pid=p.pid)
    uvicorn.run(app, host="127.0.0.1", port=8000)
    log("Finished tidy process", level=ERROR_LEVEL.INFO, pid=p.pid)
