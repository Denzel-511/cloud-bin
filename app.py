import io
from flask import Flask, render_template, request, redirect, send_file, url_for, flash
from google.cloud import storage
import os
import logging
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Secret key for session management, moved to environment variable for security
app.secret_key = os.getenv('SECRET_KEY', 'fallback-key')  # Default fallback if environment variable is not set

# Google Cloud Storage client setup
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
storage_client = storage.Client()

# Define the bucket name (ensure this is the correct bucket you've set up)
bucket_name = os.getenv('BUCKET_NAME', 'mysecuredbucket')
bucket = storage_client.get_bucket(bucket_name)

# Allowed extensions for file uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'txt', 'json'}

# Define a secure CSP configuration
Talisman(app, content_security_policy={
    'default-src': ["'self'"],
    'script-src': ["'self'", "https://trusted-cdn.com"],  # Trusted sources only
    'style-src': ["'self'", "https://fonts.googleapis.com"],  # Trusted style sources
    'img-src': ["'self'"],
    'object-src': ["'none'"],
    'frame-ancestors': ["'none'"],
    'base-uri': ["'self'"],
    'form-action': ["'self'"]
})

# Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Logging setup
logging.basicConfig(filename='app.log', level=logging.INFO)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



@app.route('/', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def home():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            logging.warning('No file part in the request')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            logging.warning('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            blob = bucket.blob(filename)
            blob.upload_from_file(file)
            flash('File uploaded successfully')
            logging.info(f'File {filename} uploaded successfully')
            return redirect(url_for('home'))
        else:
            flash('File type not allowed')
            logging.warning(f'File type not allowed: {file.filename}')
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)