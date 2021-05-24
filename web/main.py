"""A simple web application using epubmangler"""

import os
import pathlib

from fastapi import FastAPI, File, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from epubmangler import EPub

app = FastAPI()

# TODO: Needs a backend to delete everything in /upload after a while


@app.get("/")
async def main():

    # TODO: Upload a file here

    return HTMLResponse("upload a book")


@app.post("/edit")
async def edit(file: UploadFile = File(...)):
    filename = pathlib.Path('upload', file.filename)

    with open(filename, 'wb') as temp:
        temp.write(await file.read())

    try:
        epub = EPub(filename)
    except ValueError:
        os.remove(filename)
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    # TODO: This is where everything happens

    return HTMLResponse(f"editing: {epub.file}")


@app.put("/download")
async def download(filename: str):
    return FileResponse(filename)
