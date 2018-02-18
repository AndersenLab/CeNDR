import json
import pandas as pd
import numpy as np

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

from base.utils.gcloud import query_item
from base.constants import PRICES
from base.views.api.api_strain import query_strains
from base.utils.data_utils import is_number, list_duplicates
from slugify import slugify
from gcloud.exceptions import BadRequest


from logzero import logger


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
    comments = TextAreaField("Comments", [Length(min=0, max=300)])
    recaptcha = RecaptchaField()

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


#
# Perform Mapping Form
#


class TraitData(HiddenField):
    """
        A subclass of HiddenField is used to
        do the initial processing of the data
        input from the 'handsontable' structure
        on the perform mapping page.
    """
    def process_formdata(self, input_data):
        if input_data:
            self.data = input_data[0]
        else:
            self.data = None
            self.processed_data = None
            return
        self.error_items = []  # Cells to highlight as having errors
        try:
            data = json.loads(input_data[0])
        except ValueError as e:
            raise ValidationError(e.msg)

        # Read in data
        headers = data.pop(0)
        df = pd.DataFrame(data, columns=headers) \
               .replace('', np.nan) \
               .dropna(how='all') \
               .dropna(how='all', axis=1)
        if 'STRAIN' in df.columns:
            self.strain_list = list(df.STRAIN)

        # Resolve isotypes and insert as second column
        try:
            df = df.assign(ISOTYPE=[query_strains(x, resolve_isotype=True) for x in df.STRAIN])
            isotype_col = df.pop("ISOTYPE")
            df.insert(1, "ISOTYPE", isotype_col)
            logger.info(df)
        except AttributeError:
            # If the user fails to pass data it will be flagged
            pass
        self.processed_data = df


def validate_duplicate_strain(form, field):
    """
        Validates that each there are no duplicate strains listed.
    """
    df = form.trait_data.processed_data
    try:
        dup_strains = df.STRAIN[df.STRAIN.duplicated()]
        if dup_strains.any():
            dup_strains = dup_strains.values
            form.trait_data.error_items.extend(dup_strains)
            raise ValidationError(f"Duplicate Strains: {dup_strains}")
    except AttributeError:
        pass


def validate_duplicate_isotype(form, field):
    """
        Validates that each strain has a
        single associated isotype.
    """
    df = form.trait_data.processed_data
    try:
        dup_isotypes = df.STRAIN[df.ISOTYPE.duplicated()]
        if dup_isotypes.any():
            dup_isotypes = dup_isotypes.values
            form.trait_data.error_items.extend(dup_isotypes)
            raise ValidationError(f"Some strains belong to the same isotype: {dup_isotypes}")
    except AttributeError:
        pass


def validate_row_length(form, field):
    """
        Validates that a minimum of 30 strains are present.
    """
    df = form.trait_data.processed_data
    invalid_len_columns = [x for x in df.columns[2:] if df[x].notnull().sum() < 30]
    if invalid_len_columns:
        form.trait_data.error_items.extend(invalid_len_columns)
        raise ValidationError(f"A minimum of 30 strains are required. Need more values for trait(s): {invalid_len_columns}")


def validate_col_length(form, field):
    """
        Validates there are no more than 5 traits.
    """
    df = form.trait_data.processed_data
    rows, columns = df.shape
    if columns > 5:
        raise ValidationError("Only five traits can be submitted")


def validate_isotypes(form, field):
    """
        Validates that isotypes are resolved.
    """
    df = form.trait_data.processed_data
    try:
        unknown_strains = df.STRAIN[df.ISOTYPE.isnull()]
        if unknown_strains.any():
            unknown_strains = unknown_strains.values
            form.trait_data.error_items.extend(unknown_strains)
            raise ValidationError(f"Unknown isotype for the following strain(s): {unknown_strains}")
    except AttributeError:
        pass


def validate_numeric_columns(form, field):
    """
        Validates that trait fields are numeric
    """
    df = form.trait_data.processed_data
    non_numeric_values = []
    for x in df.columns[2:]:
        if any(df[x].map(is_number) == False):
            non_numeric_values.extend(df[x][df[x].map(is_number) == False].tolist())
    if non_numeric_values:
        form.trait_data.error_items.extend(non_numeric_values)
        raise ValidationError(f"Trait(s) have non-numeric values: {non_numeric_values}")


def validate_column_name_exists(form, field):
    df = form.trait_data.processed_data
    for n, x in enumerate(df.columns[2:]):
        if not x:
            raise ValidationError(f"Missing trait name in column {n+2}")


def validate_column_names(form, field):
    """
        Validates that the variable names are
        safe for R
    """
    df = form.trait_data.processed_data
    for x in df.columns[2:]:
        malformed_cols = [x for x in df.columns[2:] if slugify(x) != x and slugify(x)]
        if malformed_cols:
            form.trait_data.error_items.extend(malformed_cols)
            raise ValidationError(f"Trait names must begin with a letter and can only contain letters, numbers, dashes, and underscores. These columns need to be renamed: {malformed_cols}")


def validate_unique_colnames(form, field):
    """
        Validates that column names are unique.
    """
    df = form.trait_data.processed_data
    duplicate_col_names = list_duplicates(df.columns[1:])
    if duplicate_col_names:
        form.trait_data.error_items.extend(duplicate_col_names)
        raise ValidationError(f"Duplicate column names: {duplicate_col_names}")


def validate_report_name_unique(form, field):
    """
        Checks to ensure that the report name submitted is unique.
    """
    report_slug = slugify(form.report_name.data)
    try:
        reports = query_item('trait', filters=[('report_slug', '=', report_slug)])
        if len(reports) > 0:
            raise ValidationError(f"That report name is not available. Choose a unique report name")
    except BadRequest:
        raise ValidationError(f"Backend Error")


def validate_missing_isotype(form, field):
    """
        Checks to see whether data is
        provided for an isotype that does not exist.
    """
    df = form.trait_data.processed_data
    try:
        blank_strains = list(df[df.STRAIN.isnull()].apply(lambda row: sum(row.isnull()), axis=1).index+1)
        if blank_strains:
            raise ValidationError(f"Missing strain(s) on row(s): {blank_strains}")
    except AttributeError:
        pass


def validate_strain_w_no_data(form, field):
    """
        Checks to see whether any strains are present
        that have no associated trait data.
    """
    df = form.trait_data.processed_data
    null_counts = df.apply(lambda row: sum(row.isnull()), axis=1)
    missing_trait_data = (len(df.columns) - null_counts == 2)
    try:
        blank_traits = list(df[missing_trait_data & df.STRAIN.notnull() == True].STRAIN)
        if blank_traits:
            raise ValidationError(f"Strain(s) with no trait data: {blank_traits}")
    except AttributeError:
        pass


def validate_data_exists(form, field):
    df = form.trait_data.processed_data
    logger.info(df)
    try:
        df.STRAIN
        df.ISOTYPE
    except AttributeError:
        raise ValidationError("No data provided")


class mapping_submission_form(Form):
    """
        Form for mapping submission
    """
    report_name = StringField('Report Name', [Required(),
                                              Length(min=1, max=50),
                                              validate_report_name_unique])
    is_public = RadioField('Release', choices=[(True, 'public'), (False, 'private')], coerce=bool)
    description = TextAreaField('Description', [Length(min=0, max=1000)])
    trait_data = TraitData(validators=[validate_row_length,
                                       validate_duplicate_strain,
                                       validate_duplicate_isotype,
                                       validate_isotypes,
                                       validate_numeric_columns,
                                       validate_column_names,
                                       validate_unique_colnames,
                                       validate_column_name_exists,
                                       validate_missing_isotype,
                                       validate_strain_w_no_data,
                                       validate_data_exists])
