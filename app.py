import os
import sys
import ast
from random import choice
from string import ascii_uppercase
# We'll render HTML templates and access data sent by POST
# using the request object from flask. Redirect and url_for
# will be used to redirect the user once the upload is done
# and send_from_directory will help us to send/show on the
# browser the file that the user just uploaded
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug import secure_filename
from PyPDF2 import PdfFileMerger, PdfFileReader
import re
from flask_sqlalchemy import SQLAlchemy

# Initialize the Flask application
app = Flask(__name__)

# This is the path to the upload directory
app.config['UPLOAD_FOLDER'] = r'C:\Users\felix\Downloads\cc3093b2d8cced6dcf38-b473c48d80fc30e92d3c12fad90eb1991db0442d\uploads'
# These are the extension that we are accepting to be uploaded
app.config['ALLOWED_EXTENSIONS'] = set(['pdf'])

# For a given file, return whether it's an allowed type or not
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

#Create random string
def randomstring(length):
   return ''.join(choice(ascii_uppercase) for i in range(length))

#Bundle PDFs
#TODO: split into module rather than leave inline
def bundlePDFs(directory):
    merger = PdfFileMerger()
    tempdir = directory
    PDFs = []
    for filename in os.listdir(tempdir):
        if filename.endswith('.pdf'):
            PDFs.append(filename)
    index = 0
    current_page = 0
    for PDF in PDFs:
        m = re.search('(.*)\.pdf', PDFs[index])
        case_no = m.group(1)
        bookmark_title = 'Case '+str(case_no)
        merger.addBookmark(bookmark_title, current_page)
        merger.append(PdfFileReader(tempdir+'/'+PDFs[index], 'rb'))
        current_page = current_page + PdfFileReader(tempdir+'/'+PDFs[index], 'rb').getNumPages()
        index = index + 1
    merger.setPageMode('/UseOutlines')
    merger.write(tempdir+"\Bundle.pdf")

#SQL
#TODO: split into module rather than leave inline
#app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = r'sqlite:///C:\\Users\\felix\Downloads\\cc3093b2d8cced6dcf38-b473c48d80fc30e92d3c12fad90eb1991db0442d\\test.db'
db = SQLAlchemy(app)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), unique=False)
    folder = db.Column(db.String(10), unique=False)
    category = db.Column(db.String(100), unique=False)
    order = db.Column(db.Integer, unique=False)

    def __init__(self, filename, folder, category, order):
        self.filename = filename
        self.folder = folder
        self.category = category
        self.order = order

    def __repr__(self):
        return '<File %r>' % self.filename

# This route will show a form to perform an AJAX request
# jQuery is loaded to execute the request and update the
# value of the operation
@app.route('/')
def index():
    return render_template('index.html')


# Route that will process the file upload
@app.route('/upload', methods=['POST'])
def upload():
    # Get the name of the uploaded files
    uploaded_files = request.files.getlist("file[]")
    #filenames = []
    # Create a new folder to contain the uploaded files,
    # so they don't get mixed up with other uploads
    folder_name = randomstring(10)
    # Generate resulting full path
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    #Check whether folder_name is unique
    while os.path.isdir(full_path):
        folder_name = randomstring(10)
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    # Create that folder
    os.makedirs(full_path)
    for file in uploaded_files:
        # Check if the file is one of the allowed types/extensions
        if file and allowed_file(file.filename):
            # Make the filename safe, remove unsupported chars
            filename = secure_filename(file.filename)
            # Move the file form the temporal folder to the upload
            # folder we setup
            file.save(os.path.join(full_path, filename))
            # Save the filename into a list, we'll use it later
            #filenames.append(filename)
            # Add required info to DB
            document = Document(filename, folder_name, '', '999')
            db.session.add(document)
            db.session.commit()
            # Redirect the user to the uploaded_file route, which
            # will basicaly show on the browser the uploaded file
    # Load an html page with a link to each uploaded file
    filenames = []
    docs = Document.query.order_by(Document.order).all()
    for doc in docs:
        filenames.append(doc.filename)
    return render_template('upload.html', filenames=filenames, folder_name=folder_name)

# This route is expecting a parameter containing the name
# of a file. Then it will locate that file on the upload
# directory and show it on the browser, so if the user uploads
# an image, that image is going to be show after the upload
@app.route('/uploads/<folder_name>/<filename>')
def uploaded_file(folder_name, filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], folder_name),
                               filename)

# Additional uplaods
@app.route('/addtional_upload', methods=['POST'])
def additional_upload():
    # Existing file location
    folder_name = request.form.get('folder_name')
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    # Get the name of the uploaded files
    uploaded_files = request.files.getlist("file[]")
    # Append files already in folder_name to filenames
    filenames = os.listdir(full_path)
    # Process newly-uplaoded files
    for file in uploaded_files:
        # Check if the file is one of the allowed types/extensions
        if file and allowed_file(file.filename):
            # Make the filename safe, remove unsupported chars
            filename = secure_filename(file.filename)
            # Move the file form the temporal folder to the upload
            # folder we setup
            file.save(os.path.join(full_path, filename))
            # Save the filename into a list, we'll use it later
            #filenames.append(filename)
            # Add required info to DB
            document = Document(filename, folder_name, '', '999')
            db.session.add(document)
            db.session.commit()
            # Redirect the user to the uploaded_file route, which
            # will basicaly show on the browser the uploaded file
    # Load an html page with a link to each uploaded file
    filenames = []
    docs = Document.query.order_by(Document.order).all()
    for doc in docs:
        filenames.append(doc.filename)
    return render_template('upload.html', filenames=filenames, folder_name=folder_name)

# Additional uplaods
@app.route('/create_bundle', methods=['POST'])
def create_bundle():
    folder_name = request.form.get('folder_name')
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    directory = full_path
    bundlePDFs(directory)
    return send_from_directory(full_path,
                               'Bundle.pdf')

@app.route('/delete_file', methods=['POST'])
def delete_file():
    file_name = request.form.get('file_name')
    folder_name = request.form.get('folder_name')
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    os.remove(os.path.join(full_path, file_name))
    filenames = os.listdir(full_path)
    DB_entry = Document.query.filter_by(filename=file_name).first()
    db.session.delete(DB_entry)
    db.session.commit()
    return render_template('upload.html', filenames=filenames, folder_name=folder_name)

@app.route('/update_order')
def update_order():
    sort_order = request.args['order']
    sort_order = ast.literal_eval(sort_order)
    order = 1
    for item in sort_order:
        DB_entry = Document.query.filter_by(filename=item).first()
        DB_entry.order = order
        db.session.commit()
        order = order + 1

if __name__ == '__main__':
    app.run(
        host="0.0.0.0",
        port=int("80"),
        debug=True
    )
