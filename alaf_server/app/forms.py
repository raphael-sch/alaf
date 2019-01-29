from .models import Project
from .plots import colors

from flask import flash
from flask_wtf import FlaskForm
from wtforms import HiddenField, StringField, SubmitField, IntegerField, FieldList, FormField
from wtforms.validators import ValidationError, DataRequired, Regexp, Length


def get_letter_validator():
    """
    Validator for letters and underscore only.
    :return: ValidationError
    """
    return Regexp('^\w+$',
                  message="Only letters numbers or underscore allowed")


def length_val(min, max):
    """
    Check length of entry.
    :param min: minimum length
    :param max: maximum length
    :return: ValidationError
    """
    return Length(min=min, max=max, message="Entry must be between {} & {} characters".format(min, max))


def unique_project_name(form, field):
    """
    Check if project name already in database.
    :param form: WTForm form
    :param field: WTForm field
    :return:
    """
    project = Project.query.filter_by(name=field.data).one_or_none()

    if project is None:
        return
    if project.id != form.id.data:
        raise ValidationError('Project name already taken')


def distinct(attr, message):
    """
    Check if every model name is unique in one project.
    :param attr:
    :return:
    """
    def func(form, field):
        data = [d[attr] for d in field.data]
        if len(data) != len(set(data)):
            flash(message, 'danger')
            raise ValidationError(message)
    return func


class ModelForm(FlaskForm):
    """
    Embedded form for variable number of model names.
    """
    id = HiddenField()
    name = StringField('Name', validators=[DataRequired(),
                                           get_letter_validator(),
                                           length_val(4, 75)])

    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(meta={'csrf': False}, *args, **kwargs)


class EditProjectForm(FlaskForm):
    """
    Create and edit project. Embeds model form for flexible number of models added to a project.
    """
    submit = SubmitField('Submit')
    name = StringField('Project Name', validators=[DataRequired(),
                                                   unique_project_name,
                                                   get_letter_validator(),
                                                   length_val(4, 75)])
    id = HiddenField()
    max_count = IntegerField('Number of Instances', default=500)
    models = FieldList(FormField(ModelForm),
                       min_entries=1,
                       max_entries=len(colors),
                       validators=[DataRequired(), distinct('name', 'Model names have to be distinct')])


class DeleteProjectForm(FlaskForm):
    """
    Delete Project button
    """
    delete = SubmitField('Delete Project')

