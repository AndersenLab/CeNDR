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

import json
import pandas as pd
from base.views.api.api_strain import query_strains
def process_phenotype_data(input_data):
    try:
        data = json.loads(input_data)
    except ValueError as e:
        raise ValidationError(e.msg)
    # Read in data
    headers = data.pop(0)
    df = pd.DataFrame(data, columns=headers) \
           .dropna(thresh=1) \
           .dropna(thresh=1, axis=1)
    rows, columns = df.shape
    if rows < 30:
        raise ValidationError("A minimum of 30 strains are required.")

    # Resolve isotypes
    #print(df)
    #print(query_strains(df[['STRAIN']], list_only=True, as_scaler=True))
    df = df.assign(isotype=[query_strains(x, resolve_isotype=True) for x in df.STRAIN])
    print(df)




class mapping_submission_form(Form):
    """
        Form for mapping submission
    """
    report_name = StringField('Report Name', [Required(), Length(min=1, max=50)])
    is_public = RadioField('Release', choices=[("True", 'public'), ("False", 'private')])
    description = TextAreaField('Description', [Length(min=0, max=1000)])
    phenotype_data = HiddenField()

    def validate_phenotype_data(form, field):
        phenotype_data = form.phenotype_data.data
        data = process_phenotype_data(phenotype_data)



