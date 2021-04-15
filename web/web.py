#!/usr/bin/env python
"""A flask application using the epubmangler library."""

import os, os.path

from epubmangler import EPub, is_epub

import jinja2
from flask import Flask, redirect, request, send_from_directory, url_for

from werkzeug.utils import secure_filename

# TODO: Delete files in uploads every 10 minutes or whatever

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/home/david/Projects/epubmangler/web/uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 # 10 Mb

@app.route('/')
def index():
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="/upload" method=post enctype=multipart/form-data>
        <input type=file name=file>
        <input type=submit value=Upload>
    </form>
    '''

@app.route('/edit/<filename>')
def edit(filename):
    try:
        book = EPub(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        author = book.get('creator')
        title = book.get('title')
        
        return f'''
        <!doctype html>
        <title>Editing: {filename}</title>
        <h1>Editing: {filename}</h1>
        <form action="/save" method=post enctype=multipart/form-data>
            <input type=hidden name=filename value={filename}>
            <input type=text name=author value={author}>
            <input type=text name=title value={title}>
            <input type=submit value=Save>
        </form>
        '''
    
    except ValueError:
        return 'not an epub'

@app.route('/save', methods=['POST', 'GET'])
def save():
    if request.method == 'POST':
        filename = request.form['filename']
        book = EPub(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        book.set('title', request.form['title'])
        book.set('creator', request.form['author'])
        book.save(os.path.join(app.config['UPLOAD_FOLDER'], filename), overwrite=True)
        
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    else:
        return redirect(url_for('index'))

@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST':

        try:
            file = request.files['file']
        except KeyError:
            return 'no file'

        try:
            ext = os.path.splitext(file.filename)[1]
        except IndexError:
            return 'not an epub'
        
        if ext != '.epub':
            return 'not an epub'
        
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        return redirect(url_for('edit', filename=filename))

    else:
        return redirect(url_for('index'))
