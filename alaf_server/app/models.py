from . import db


class Project(db.Model):
    """
    Project table in database.
    """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(75), unique=True)
    max_count = db.Column(db.Integer)

    models = db.relationship("Model", backref='project', cascade="all, delete-orphan")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Instance(db.Model):
    """
    Instance table in database.
    """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    model_id = db.Column(db.Integer, db.ForeignKey('model.id'))
    utterance = db.Column(db.Text)
    annotation = db.Column(db.Integer, nullable=True)
    client_time = db.Column(db.Float, nullable=True)
    al_time = db.Column(db.Float, nullable=True)
    io_time = db.Column(db.Float, nullable=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Model(db.Model):
    """
    Model table in databse.
    """
    __table_args__ = (db.Index('model_name_project_id_uindex', 'name', 'project_id'), )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(75))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    sid = db.Column(db.String(100))
    count = db.Column(db.Integer)

    instances = db.relationship("Instance", backref='model', cascade="all, delete-orphan")
    scores = db.relationship("Score", backref='model', cascade="all, delete-orphan")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Score(db.Model):
    """
    Score table in database.
    """
    count = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey('model.id'), primary_key=True)
    f1 = db.Column(db.Float)
    precision = db.Column(db.Float)
    recall = db.Column(db.Float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
