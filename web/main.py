import pathlib

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from epubmangler import EPub

app = FastAPI()

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
        return RedirectResponse("/")
    
    # TODO: This is where everything happens
    
    return HTMLResponse(f"editing: {epub.opf}")

@app.put("/download")
async def download(filename: str):
    return FileResponse(filename)
