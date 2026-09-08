from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, TextAreaField, FloatField, SelectField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, NumberRange, InputRequired

from flask_login import current_user
from flask_wtf.file import FileField, FileAllowed

from models import User


class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=30)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=50)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

    submit = SubmitField('Register')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.lower()).first()

        if user:
            raise ValidationError('Email already registered.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('LogIn')


class EventForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=5, max=150)])
    short_description = StringField('Short Description', validators=[DataRequired(), Length(min=5, max=250)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=20)])
    location = StringField('Location', validators=[DataRequired(), Length(min=1, max=150)])
    date = DateTimeLocalField('Event Date and Time', format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    ticket_price = FloatField('Ticket Price', validators=[InputRequired(), NumberRange(min=0)])
    organizer = StringField('Organizer', validators=[DataRequired(), Length(min=1, max=150)])
    category = SelectField(
        'Category',
        choices=[
            ("", "Select Category"),
            ("Music", "Music"),
            ("Technology", "Technology"),
            ("Sport", "Sport"),
            ("Art", "Art"),
            ("Education", "Education"),
            ("Other", "Other")
        ],
        validators=[DataRequired()]
    )

    submit = SubmitField('Submit')

class DeleteForm(FlaskForm):
    submit = SubmitField('Delete')

class ProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50)])

    email = StringField('Email', validators=[DataRequired(), Email()])

    picture = FileField('Profile Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg'],
                                                                   "Only JPEG and PNG images are allowed."
                                                                   )
                                                       ]
                        )

    submit = SubmitField('Update Profile')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.lower()).first()

        if user and user.id != current_user.id:
            raise ValidationError('Email already registered.')

