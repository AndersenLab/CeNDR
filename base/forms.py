from base.application import app
from flask_wtf import Form
from wtforms import StringField, TextAreaField, IntegerField
from wtforms.validators import Required, Length, Email 
from flask_wtf import RecaptchaField


class donation_form(Form):
    """
        The donation form
    """
    name = StringField('Name', [Required(), Length(min=3, max=100)])
    address = TextAreaField('Address', [Length(min=10, max=200)])
    email = StringField('Email', [Email(), Length(min=3, max=100)])
    total = IntegerField('Donation Amount')
    recaptcha = RecaptchaField()