import os

DEBUG = True

# localhost for local and 0.0.0.0 for external access
HOST = 'localhost'
PORT = '5000'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# sqlite path
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'db', 'sqlite.db')
SQLALCHEMY_TRACK_MODIFICATIONS = True
DATABASE_CONNECT_OPTIONS = {}


# secret key for form validation
SECRET_KEY = "Yy7l6HjoXfWgfCNstQCdbz5rGctSK35C"
WTF_CSRF_SECRET_KEY = "LVZYwwyXeBnYi1OHMu0kexxmlYW3hErp"