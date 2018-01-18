from base.application import app
from flask_wtf import Form, RecaptchaField
from wtforms import (StringField,
                     TextAreaField,
                     IntegerField,
                     SelectField,
                     FieldList,
                     HiddenField,
                     RadioField)
from wtforms.validators import Required, Length, Email, DataRequired
from wtforms.validators import ValidationError
from base.constants import PRICES


class donation_form(Form):
    """
        The donation form
    """
    name = StringField('Name', [Required(), Length(min=3, max=100)])
    address = TextAreaField('Address', [Length(min=10, max=200)])
    email = StringField('Email', [Email(), Length(min=3, max=100)])
    total = IntegerField('Donation Amount')
    recaptcha = RecaptchaField()



SHIPPING_OPTIONS = [('UPS', 'UPS'),
                    ('FEDEX', 'FEDEX'),
                    ('Flat Rate Shipping', '${} Flat Fee'.format(PRICES.SHIPPING))]

PAYMENT_OPTIONS = [('check', 'Check'),
                   ('credit_card', 'Credit Card')]


class order_form(Form):
    """
        The strain order form
    """
    name = StringField('Name', [Required(), Length(min=3, max=100)])
    email = StringField('Email', [Email(), Length(min=3, max=100)])
    address = TextAreaField('Address', [Length(min=10, max=200)])
    phone = StringField('Phone', [Length(min=3, max=35)])
    shipping_service = SelectField('Shipping', choices=SHIPPING_OPTIONS)
    shipping_account = StringField('Account Number')
    items = FieldList(HiddenField('item', [DataRequired()]))
    payment = SelectField("Payment", choices=PAYMENT_OPTIONS)
    #recaptcha = RecaptchaField()

    def validate_shipping_account(form, field):
        """
            Ensure the user supplies an account number
            when appropriate.
        """
        if form.shipping_service.data != "Flat Rate Shipping" and not field.data:
            raise ValidationError("Please supply a shipping account number.")
        elif form.shipping_service.data == "Flat Rate Shipping" and field.data:
            raise ValidationError("No shipping account number is needed if you are using flat-rate shipping.")


    def item_price(self):
        """
            Fetch item and its price
        """
        for item in self.items:
            if item.data == "set_divergent":
                yield item.data, PRICES.DIVERGENT_SET
            elif item.data.startswith("set"):
                yield item.data, PRICES.STRAIN_SET
            else:
                yield item.data, PRICES.STRAIN
        if self.shipping_service.data == "Flat Rate Shipping":
            yield "Flat Rate Shipping", PRICES.SHIPPING

    @property
    def total(self):
        """
            Calculates the total price of the order
        """
        total_price = 0
        for item, price in self.item_price():
            total_price += price
        return total_price


class mapping_submission_form(Form):
    """
        Form for mapping submission
    """
    report_name = StringField('Report Name', [Required(), Length(min=1, max=50)])
    is_public = RadioField('Release', choices=[("True", 'public'), ("False", 'private')])
    description = TextAreaField('Description', [Length(min=1, max=1000)])
    phenotype_data = HiddenField()

    def validate_phenotype_data(form, field):
        pass



