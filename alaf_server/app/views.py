from . import app, db
from .models import Project, Instance, Model
from .forms import EditProjectForm, DeleteProjectForm
from .sockets import send_annotation
from .plots import scores_f1_plot, scores_precision_plot, scores_recall_plot, \
    al_time_plot, io_time_plot, client_time_plot, pos_neg_ratio_plot

from flask import request, jsonify, render_template, redirect, flash
import json
from random import choice


@app.route('/', methods=['GET', 'POST'])
@app.route('/projects/', methods=['GET'])
def projects():
    """
    Landing page
    :return:
    """
    rows = Project.query.all()
    return render_template('projects.html',
                           rows=rows)


@app.route('/project/<int:project_id>/', methods=['GET'])
@app.route('/project/<int:project_id>/overview', methods=['GET', 'POST'])
def project_overview(project_id):
    """
    Project overview with project name, max_count and automatically updated
    model connection status.
    :param project_id:
    :return: render project overview
    """
    project = Project.query.get(project_id)
    form = DeleteProjectForm()

    # delete button
    if form.delete.data is True:
        db.session.delete(project)
        db.session.commit()
        flash("Project '{}' deleted".format(project.name), 'danger')
        return redirect('projects')

    return render_template('overview.html', project=project, form=form)


@app.route('/project/<int:project_id>/insights', methods=['GET', 'POST'])
def project_insights(project_id):
    """
    Load data and create frames for plots using bokeh.
    :param project_id:
    :return: render insights page
    """
    project = Project.query.get(project_id)

    # scores
    div_scores_f1, script_scores_f1 = scores_f1_plot(project_id)
    div_scores_precision, script_scores_precision = scores_precision_plot(project_id)
    div_scores_recall, script_scores_recall = scores_recall_plot(project_id)
    # time
    div_al_time, script_al_time = al_time_plot(project_id)
    div_io_time, script_io_time = io_time_plot(project_id)
    div_client_time, script_client_time = client_time_plot(project_id)
    # stats
    div_pos_neg_plot, script_pos_neg_plot = pos_neg_ratio_plot(project_id)
    stats = []
    for model in project.models:
        num_pos = Instance.query.filter(db.and_(Instance.annotation.is_(1), Instance.model_id == model.id)).count()
        num_neg = Instance.query.filter(db.and_(Instance.annotation.is_(0), Instance.model_id == model.id)).count()
        stats.append((model.name, num_pos, num_neg))

    return render_template('insights.html', project=project,
                           div_scores_f1=div_scores_f1, script_scores_f1=script_scores_f1,
                           div_scores_precision=div_scores_precision, script_scores_precision=script_scores_precision,
                           div_scores_recall=div_scores_recall, script_scores_recall=script_scores_recall,
                           div_al_time=div_al_time, script_al_time=script_al_time,
                           div_io_time=div_io_time, script_io_time=script_io_time,
                           div_client_time=div_client_time, script_client_time=script_client_time,
                           div_pos_neg_plot=div_pos_neg_plot, script_pos_neg_plot=script_pos_neg_plot,
                           stats=stats
                           )


@app.route('/project/<int:project_id>/annotation', methods=['GET', 'POST'])
def project_annotation(project_id):
    """
    Annotation page. Javascript continuously queries for new utterances.
    :param project_id:
    :return: render annotation page
    """
    project = Project.query.get(project_id)
    return render_template('annotation.html',
                           project=project)


@app.route('/create_project', methods=('GET', 'POST'))
def create_project():
    """
    Create project form. Validate project and model names before creation.
    :return: render create project form
    """
    form = EditProjectForm()
    if form.validate_on_submit():
        project = Project(name=form.data['name'],
                          max_count=form.data['max_count'])
        for model_data in form.data['models']:
            model = Model(name=model_data['name'])
            project.models.append(model)
        db.session.add(project)
        db.session.commit()
        flash("Project '{}' created".format(project.name), 'success')
        return redirect('/project/{}/overview'.format(project.id))
    models = [{'value': m.data['name'], 'errors': m.errors.get('name', [])} for m in form.models]
    return render_template('edit_project.html', form=form, models=models, action="/create_project")


@app.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
def edit_project(project_id):
    """
    Edit project form. Populate fields with values from database.
    :param project_id:
    :return: render edit project form
    """
    project = Project.query.get(project_id)
    form = EditProjectForm(obj=project)

    if form.validate_on_submit():
        project.name = form.data['name']
        project.max_count = form.data['max_count']

        model_data_ids = set(m['id'] for m in form.data['models'])
        delete_models = [model.id for model in project.models if str(model.id) not in model_data_ids]

        for model_data in form.data['models']:
            model = Model.query.get(model_data['id'])
            if model is None:
                model = Model(name=model_data['name'], project_id=project.id)
                flash('Created model: {}'.format(model.name), 'success')
                db.session.add(model)
            elif model.name != model_data['name']:
                model.name = model_data['name']
                flash("Changed name of model '{}' to '{}'".format(model.name, model_data['name']), 'success')

        for model_id in delete_models:
            model = Model.query.get(model_id)
            flash("Deleted model '{}'".format(model.name), 'success')
            db.session.delete(model)

        db.session.commit()
        return redirect('/project/{}/overview'.format(project.id))

    models = [{'value': m.data['name'], 'errors': m.errors.get('name', []), 'id': m.data['id']} for m in form.models]
    action = "/project/{}/edit".format(project_id)
    return render_template('edit_project.html', project=project, form=form, models=models, action=action)


@app.route('/annotate', methods=['POST'])
def annotate():
    """
    Receives annotation from the frontend.
    :return: empty response
    """
    data = json.loads(request.data.decode())
    annotation = data["annotation"]  # int
    instance_id = data["instance_id"]

    if instance_id is None:
        return "no instance id found", 400

    instance = Instance.query.get(instance_id)
    instance.annotation = annotation
    db.session.commit()

    send_annotation(instance)
    return jsonify({})


@app.route('/project/<int:project_id>/instance/next')
def next_instance(project_id):
    """
    Query to select next unannotated instance. Called by javascript from frontend.
    :param project_id:
    :return: json: instance_id, utterance
    """
    instances = Instance.query.filter(db.and_(Instance.annotation.is_(None),
                                              Instance.project_id == project_id)).all()
    max_count_diff = 5
    if len(instances) == 0:
        message = "No instance without annotation left"
        print(message)
        return message, 500

    models = Model.query.filter_by(project_id=project_id).order_by(Model.count).all()
    # check the difference in annotated instances (count) between
    # model with lowest count and highest count
    if models[-1].count - models[0].count > max_count_diff:
        instances = list(filter(lambda i: i.model_id == models[0].id, instances))
        if len(instances) == 0:
            raise AttributeError('Count difference higher than {}'.format(max_count_diff))

    instance = choice(instances)
    return jsonify({'instance_id': instance.id,
                    'utterance': instance.utterance})


@app.route('/project/<int:project_id>/status')
def check_model_status(project_id):
    """
    Query model status. Model is online if sid is saved in database.
    Called from javascript in frontend
    :param project_id:
    :return: model name, connection status, current annotated instances
    """
    project = Project.query.get(project_id)
    response = list()
    for model in project.models:
        status = model.sid is not None
        count = model.count
        if count is not None:
            count += 1
        response.append({'name': model.name, 'status': status, 'count': count})
    return jsonify(models=response)
