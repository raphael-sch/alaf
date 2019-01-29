from . import db
from .models import Instance, Project

from bokeh.plotting import figure
from bokeh.embed import components

colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2',
          '#7f7f7f', '#bcbd22', '#17becf', '#aec7e8', '#ffbb78', '#98df8a', '#ff9896',
          '#c5b0d5', '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5']


def get_plot(project_id, data_func, title, x_axis_label, y_axis_label, avg=False):
    """
    Helper function to build plot using bokeh.
    :param project_id: project id
    :param data_func: returns x and y data
    :param title: title of plot
    :param x_axis_label: label of x axis
    :param y_axis_label: label of y axis
    :param avg: weather to compute the average of avgN_x models
    :return: bokeh components of plot
    """
    project = Project.query.get(project_id)

    plot = figure(title=title, x_axis_label=x_axis_label, y_axis_label=y_axis_label)
    avg_data = dict()
    for i, model in enumerate(project.models):
        x_data, y_data = data_func(model)

        name = model.name
        if avg and name.startswith('avg'):
            name = 'avg ' + '_'.join(model.name.split('_')[1:])
        if name not in avg_data:
            avg_data[name] = dict()
        for x, y in zip(x_data, y_data):
            avg_data[name][x] = avg_data[name].get(x, []) + [y]

    for i, name in enumerate(avg_data):
        if len(avg_data[name]) == 0:
            continue
        x, y = zip(*sorted(avg_data[name].items()))
        if len(y[0]) > 1:
            name += ' ({})'.format(len(y[0]))
        y = [sum(e) / float(len(e)) for e in y]

        plot.line(x, y, legend=name, line_width=2, line_color=colors[i])
    plot.legend.location = "top_left"
    return components(plot)


def scores_f1_plot(project_id):
    """
    Build plot for F1 score.
    :param project_id:
    :return: bokeh components
    """
    def data_func(model):
        return [s.count for s in model.scores], [s.f1 for s in model.scores]

    return get_plot(project_id=project_id,
                    data_func=data_func,
                    title="Active Learning Model F1 Score",
                    x_axis_label='number of AL instances',
                    y_axis_label='F1 score',
                    avg=True)


def scores_precision_plot(project_id):
    """
    Build plot for precision score.
    :param project_id:
    :return: bokeh components
    """
    def data_func(model):
        return [s.count for s in model.scores], [s.precision for s in model.scores]

    return get_plot(project_id=project_id,
                    data_func=data_func,
                    title="Active Learning Model Precision",
                    x_axis_label='number of AL instances',
                    y_axis_label='Precision score',
                    avg=True)


def scores_recall_plot(project_id):
    """
    Build plot for recall score.
    :param project_id:
    :return: bokeh components
    """
    def data_func(model):
        return [s.count for s in model.scores], [s.recall for s in model.scores]

    return get_plot(project_id=project_id,
                    data_func=data_func,
                    title="Active Learning Model Recall",
                    x_axis_label='number of AL instances',
                    y_axis_label='Recall score',
                    avg=True)


def al_time_plot(project_id):
    """
    Build plot for active learning time.
    :param project_id:
    :return: bokeh components
    """
    def data_func(model):
        instances = Instance.query.filter_by(model_id=model.id).order_by(Instance.id).all()
        return [i for i in range(len(instances))], [i.al_time for i in instances]

    return get_plot(project_id=project_id,
                    data_func=data_func,
                    title="Active Learning Model Runtime",
                    x_axis_label='number of AL instances',
                    y_axis_label='seconds')


def io_time_plot(project_id):
    """
    Build plot for I/O time.
    :param project_id:
    :return: bokeh components
    """
    def data_func(model):
        instances = Instance.query.filter_by(model_id=model.id).order_by(Instance.id).all()
        return [i for i in range(len(instances))], [i.io_time for i in instances]

    return get_plot(project_id=project_id,
                    data_func=data_func,
                    title="SocketIO Communication Overhead",
                    x_axis_label='number of AL instances',
                    y_axis_label='seconds')


def client_time_plot(project_id):
    """
    Build plot for time spent on client.
    :param project_id:
    :return: bokeh components
    """
    def data_func(model):
        instances = Instance.query.filter_by(model_id=model.id).order_by(Instance.id).all()
        return [i for i in range(len(instances))], [i.client_time for i in instances]

    return get_plot(project_id=project_id,
                    data_func=data_func,
                    title="Total Time Spent on Client",
                    x_axis_label='number of AL instances',
                    y_axis_label='seconds')


def pos_neg_ratio_plot(project_id):
    """
    Build plot for ratio between positive and negative instances.
    :param project_id:
    :return: bokeh components
    """
    def data_func(model):
        annotations = Instance.query.with_entities(Instance.annotation)\
            .filter(db.and_(Instance.annotation.isnot(None),
                            Instance.model_id == model.id))\
            .order_by(Instance.id).all()

        y = list()
        pos_neg = {1: 0, 0: 0}
        for annotation in annotations:
            pos_neg[annotation[0]] += 1
            pos, neg = float(pos_neg[1]), pos_neg[0]
            ratio = (pos / neg) if neg > 0 else 0
            y.append(ratio)

        return [i for i in range(len(annotations))], y

    return get_plot(project_id=project_id,
                    data_func=data_func,
                    title="Ratio of positive to negative annotations",
                    x_axis_label='number of AL instances',
                    y_axis_label='pos/neg',
                    avg=True)
