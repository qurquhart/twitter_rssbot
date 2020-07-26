from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, PasswordField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, ValidationError, URL, EqualTo, Length
from app.models import User
from wtforms.fields.html5 import TimeField
import wtforms


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    # noinspection PyMethodMayBeStatic
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Username already in use.')

    # noinspection PyMethodMayBeStatic
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Email already in use.')


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    about_me = TextAreaField('About me', validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Please use a different username.')


class PostForm(FlaskForm):
    post = TextAreaField('Say something', validators=[
        DataRequired(), Length(min=1, max=140)])
    submit = SubmitField('Submit')


class RssForm(FlaskForm):
    post = StringField('', validators=[
        DataRequired(), URL(), Length(min=1, max=140)])
    submit = SubmitField('Submit')


class RssRemove(FlaskForm):
    submit = SubmitField('Remove')


class CreatePosts(FlaskForm):
    submit = SubmitField('Create Posts')


class AutoPostInterval(FlaskForm):
    interval = IntegerField('', validators=[DataRequired()])
    submit = SubmitField('Save')


class RefreshInterval(FlaskForm):
    interval = IntegerField('', validators=[DataRequired()])
    submit = SubmitField('Save')


class AutoPostDuration(FlaskForm):
    time_start = TimeField('', validators=[DataRequired()])
    time_end = TimeField('', validators=[DataRequired()])
    submit2 = SubmitField('save')


class PostSettings(FlaskForm):
    interval = wtforms.FormField(AutoPostInterval)
    duration = wtforms.FormField(AutoPostDuration)
    refresh = wtforms.FormField(RefreshInterval)
