from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

app = Flask(__name__)
bootstrap = Bootstrap(app)
app.config.from_pyfile('../config.py')
db = SQLAlchemy(app)

async_mode = None  # "threading"
socketio = SocketIO(app, async_mode=async_mode)

from . import views
from . import sockets
from . import models
