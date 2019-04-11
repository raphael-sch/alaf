from . import db, socketio
from .models import Project, Instance, Model, Score
import time
from flask import request
from sqlalchemy.orm.exc import NoResultFound


@socketio.on('utterance', namespace='/model')
def receive_utterance(message):
    """
    Receive utterance from client, calculate computation times and save everything in database.
    :param message: utterance, times, count
    :return:
    """
    client_time = message['client_time']
    al_time = message['al_time']
    io_time = (time.time() - message['io_time_start']) - client_time
    count = message['count']
    utterance = message['utterance']
    model = Model.query.filter_by(sid=request.sid).one_or_none()
    project = Project.query.get(model.project_id)

    # if max_count is reached, finish client
    if count >= project.max_count:
        print("model: '{}' finished with {} instances".format(model.name, model.count))
        socketio.emit('finished',
                      {'cause': "max count: {} reached".format(project.max_count)},
                      room=model.sid,
                      namespace='/model')
        model.sid = None
        db.session.commit()
        return

    # default None. Clients can send annotation in case of baselines from annotated data
    annotation = message.get('label')

    show_time = None
    submit_time = None
    copied = 0
    found_instance = None

    # code to copy already labeled instances if present in database.
    # TODO: add option to activate this in project settings
    # if instance found in db, use this label
    #found_instance = Instance.query.filter_by(utterance=utterance).first()
    #if found_instance is not None and annotation is None:
    #    annotation = found_instance.annotation
    #    show_time = time.time()
    #    submit_time = show_time + (found_instance.submit_time - found_instance.show_time)
    #    copied = 1

    model.count = count
    instance = Instance(utterance=utterance,
                        annotation=annotation,
                        project_id=model.project_id,
                        model_id=model.id,
                        client_time=client_time,
                        al_time=al_time,
                        io_time=io_time,
                        show_time=show_time,
                        submit_time=submit_time,
                        copied=copied)
    db.session.add(instance)
    db.session.commit()

    # instance was found in database and automatically labeled
    if found_instance is not None and message.get('label') is None and annotation is not None:
        print('instance found in database, label: {}'.format(annotation))
        send_annotation(instance)

    print(message)


@socketio.on('scores', namespace='/model')
def receive_scores(message):
    """
    Receive scores from client and store them with count in database.
    :param message: model_id, scores, count
    :return:
    """
    model = Model.query.filter_by(sid=request.sid).one_or_none()
    score = Score(model_id=model.id,
                  precision=message['precision'],
                  recall=message['recall'],
                  f1=message['f1'],
                  count=message['count'])
    db.session.add(score)
    db.session.commit()
    print(message)


@socketio.on('register', namespace='/model')
def on_register(message):
    """
    Check if project and model name are sent by client are available in database.
    If available, tag as online and ask for next utterance, otherwise send finished message to client.
    :param message: project_name, model_name
    :return:
    """
    project_name = message['project_name']
    model_name = message['model_name']

    try:
        project = Project.query.filter_by(name=project_name).one()
        model = Model.query.filter_by(project_id=project.id, name=model_name).one()
    except (AttributeError, NoResultFound) as e:
        socketio.emit('finished',
                      {'cause': 'project_name: {} or model_name: {} not found'.format(project_name,
                                                                                      model_name)},
                      room=request.sid,
                      namespace='/model')
        print('Client with wrong project_name or model_name tried to connect')
        return

    model.sid = request.sid
    model.count = message['count']
    db.session.commit()

    instance = Instance.query.filter(db.and_(Instance.annotation.is_(None),
                                             Instance.model_id == model.id)).first()
    if instance is None:
        socketio.emit('next_utterance',
                      {'io_time_start': time.time()},
                      room=model.sid,
                      namespace='/model')


@socketio.on('connect', namespace='/model')
def on_connect():
    """
    Connect event.
    :return:
    """
    print('connect: ' + request.sid)


@socketio.on('disconnect', namespace='/model')
def on_disconnect():
    """
    Mark client as disconnected by deleting sid from model in databse.
    :return:
    """
    model = Model.query.filter_by(sid=request.sid).one_or_none()
    if model:
        model.sid = None
        db.session.commit()
    print('disconnect: ' + request.sid)


def send_annotation(instance):
    """
    Send human annotation to client.
    :param instance:
    :return:
    """
    if instance.annotation is None:
        print('tried to send instance without annotation: {}'.format(instance))
        return
    model = Model.query.get(instance.model_id)
    io_time_start = time.time()
    message = {'utterance': instance.utterance,
               'annotation': instance.annotation,
               'io_time_start': io_time_start}
    socketio.emit('annotation',
                  message,
                  room=model.sid,
                  namespace='/model')

