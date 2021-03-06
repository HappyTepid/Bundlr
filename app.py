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
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
from werkzeug import secure_filename
from PyPDF2 import PdfFileMerger, PdfFileReader
import pdfkit
import re
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, required

class addComments(FlaskForm):
    filename = StringField('File name', validators=[DataRequired()])
    filecomments = TextAreaField('File comments', validators=[DataRequired()])

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = 'dfghndtudrug87vdfsghdf'

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
def bundlePDFs(directory, folder_name):
    merger = PdfFileMerger(strict=False)
    tempdir = directory
    PDFs = []
    global error
    error = []
    docs = Document.query.filter_by(folder=folder_name).order_by(Document.order).all()
    for doc in docs:
        PDFs.append(doc.filename)
    index = 0
    current_page = 0
    for PDF in PDFs:
        m = re.search('(.*)\.pdf', PDFs[index])
        case_no = m.group(1)
        bookmark_title = 'Case '+str(case_no)
        merger.addBookmark(bookmark_title, current_page)
        try:
            merger.append(PdfFileReader(tempdir+'/'+PDFs[index], 'rb'))
        except:
            error.append('File ' + PDFs[index] + ' is an invalid PDF. Convert it using Adobe Reader and re-upload it.')
            index = index + 1
            continue
        current_page = current_page + PdfFileReader(tempdir+'/'+PDFs[index], 'rb').getNumPages()
        index = index + 1
    if error:
        raise ValueError("invalid files detected!")
    merger.setPageMode('/UseOutlines')
    merger.write(os.path.join(tempdir, "Bundle.pdf"))

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
    #return render_template('index.html')
    return render_template('upload.html', filenames=[], folder_name='')


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
    session['folder_name'] = folder_name
    file_order = 1
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
            document = Document(filename, folder_name, '', file_order)
            db.session.add(document)
            db.session.commit()
            file_order = file_order + 1
            # Redirect the user to the uploaded_file route, which
            # will basicaly show on the browser the uploaded file
    # Load an html page with a link to each uploaded file
    filenames = []
    docs = Document.query.filter_by(folder=folder_name).order_by(Document.order).all()
    for doc in docs:
        filenames.append(doc.filename)
        #return render_template('upload.html', filenames=filenames, folder_name=folder_name, form=form)
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
    try:
        highest_order = Document.query.filter_by(folder=folder_name).order_by(Document.order.desc()).first().order
    except:
        highest_order = 0
    file_order = highest_order + 1
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
            document = Document(filename, folder_name, '', file_order)
            db.session.add(document)
            db.session.commit()
            file_order = file_order + 1
            # Redirect the user to the uploaded_file route, which
            # will basicaly show on the browser the uploaded file
    # Load an html page with a link to each uploaded file
    filenames = []
    docs = Document.query.filter_by(folder=folder_name).order_by(Document.order).all()
    for doc in docs:
        filenames.append(doc.filename)
    return render_template('upload.html', filenames=filenames, folder_name=folder_name)

# Additional uplaods
@app.route('/create_bundle', methods=['POST'])
def create_bundle():
    folder_name = request.form.get('folder_name')
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    directory = full_path
    # Verify files are valid
    PDFs = []
    error = []
    for filename in os.listdir(directory):
        if filename.endswith('.pdf'):
            PDFs.append(filename)
    for PDF in PDFs:
        try:
            with open(os.path.join(directory, PDF), "rb") as f:
                input = PdfFileReader(f, "rb")
        except:
            error.append(PDF + " is malformed, please convert it and re-upload!")
    # Create bundle
    try:
        bundlePDFs(directory, folder_name)
    except:
        #Returned by bundlePDFs - there has to be a better way to handle this though...
        global error
        return render_template('upload.html', filenames=PDFs, folder_name=folder_name, error=error)
    else:
        return send_from_directory(full_path,
                                'Bundle.pdf', as_attachment=True)

@app.route('/add_comments', methods=['POST'])
def add_comments():
    folder_name = request.form.get('folder_name')
    comments = request.form.get('comments')
    filename = request.form.get('filename')
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    pdfkit.from_string(comments, base_path+'/'+filename+'.pdf')
    try:
        highest_order = Document.query.filter_by(folder=folder_name).order_by(Document.order.desc()).first().order
    except:
        highest_order = 0
    file_order = highest_order + 1
    document = Document(filename+'.pdf', folder_name, '', file_order)
    db.session.add(document)
    db.session.commit()
    filenames = []
    docs = Document.query.filter_by(folder=folder_name).order_by(Document.order).all()
    for doc in docs:
        filenames.append(doc.filename)
    return render_template('upload.html', filenames=filenames, folder_name=folder_name)

@app.route('/delete_file', methods=['POST'])
def delete_file():
    file_name = request.form.get('file_name')
    folder_name = request.form.get('folder_name')
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
    #TODO:
    #Deleting a file needs to decrement the order of all subsequent files by 1
    os.remove(os.path.join(full_path, file_name))
    filenames = os.listdir(full_path)
    deleted_item_order = Document.query.filter_by(filename=file_name, folder=folder_name).first().order
    db.engine.execute("UPDATE document set [order] = [order] - 1 where [order] >" + str(deleted_item_order))
    Document.query.filter_by(filename=file_name, folder=folder_name).delete()
    db.session.commit()
    filenames = []
    docs = Document.query.filter_by(folder=folder_name).order_by(Document.order).all()
    for doc in docs:
        filenames.append(doc.filename)
    return render_template('upload.html', filenames=filenames, folder_name=folder_name)

@app.route('/update_order')
def update_order():
    sort_order = request.args['order']
    sort_order = ast.literal_eval(sort_order)
    folder_name = request.args['folder']
    order = 1
    for item in sort_order:
        DB_entry = Document.query.filter_by(filename=item, folder=folder_name).first()
        DB_entry.order = order
        db.session.commit()
        order = order + 1

@app.route('/write_comments', methods=['GET', 'POST'])
def write_comments():
    form = addComments()
    if form.validate_on_submit():
        folder_name = session['folder_name']
        comments = form.filecomments.data
        filename = form.filename.data
        base_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
        pdfkit.from_string(comments, base_path+'/'+filename+'.pdf')
        try:
            highest_order = Document.query.filter_by(folder=folder_name).order_by(Document.order.desc()).first().order
        except:
            highest_order = 0
        file_order = highest_order + 1
        document = Document(filename+'.pdf', folder_name, '', file_order)
        db.session.add(document)
        db.session.commit()
        filenames = []
        docs = Document.query.filter_by(folder=folder_name).order_by(Document.order).all()
        for doc in docs:
            filenames.append(doc.filename)
        return render_template('upload.html', filenames=filenames, folder_name=folder_name)
    else:
        return render_template('write_comments.html', form=form)

if __name__ == '__main__':
    app.run(
        host="0.0.0.0",
        port=int("80"),
        debug=True
    )
