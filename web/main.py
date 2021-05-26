"""A simple web application using epubmangler"""

import os
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from epubmangler import EPub

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

    inner_html = f"""editing: {epub.file}
    <form action="/download" method="POST">
    <input type="hidden" name="filename" value="{filename}" />
    <button type="submit">Save</button>
    </form>"""

    return HTMLResponse(template.replace("{{ body }}", inner_html))


@app.post("/download")
async def download(filename: str = Form(...)):
    if Path(filename).parent != Path("upload"):
        return HTMLResponse(template.replace("{{ body }}", f"bad request: {filename}"))

    inner_html = f"downloading: {filename}"

    return HTMLResponse(template.replace("{{ body }}", inner_html))
