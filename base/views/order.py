#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

These views handle strain orders

"""
import uuid
from base.forms import order_form
from base.config import config
from base.utils.email import send_email, ORDER_SUBMISSION_EMAIL
from base.utils.google_sheets import add_to_order_ws, lookup_order
from flask import render_template, request, url_for, redirect, Blueprint, abort, flash, session
from datetime import datetime
from base.utils.data_utils import chicago_date, hash_it

order_bp = Blueprint('order',
                     __name__,
                     template_folder='order')

#
# Strain Catalog
#

# --> Listed on the /strain.py page

#
# Strain Ordering Pages
#

@order_bp.route("/", methods=['GET', 'POST'])
def order():
    return redirect(url_for('strain.strain_catalog'))



@order_bp.route('/create', methods=['GET', 'POST'])
def order_page():
    """
        This view handles the order page.
    """
    form = order_form()
    if session.get('user') and not form.email.data:
        form.email.data = session.get('user')['user_email']

    # Fetch items
    items = form.items.data

    title = "Order"

    if (len(items) == 0):
        flash("You must select strains/sets from the catalog", 'error')
        return redirect(url_for("strain.strain_catalog"))

    # Is the user coming from the catalog?
    user_from_catalog = request.form.get('from_catalog') == "true"

    # When the user confirms their order it is processed below.
    if user_from_catalog is False and form.validate_on_submit():

        order_obj = {'total': form.total,
                     'date': chicago_date(),
                     'is_donation': False}
        order_obj.update(form.data)
        order_obj['phone'] = order_obj['phone'].strip("+")
        order_obj['items'] = '\n'.join(sorted([u"{}:{}".format(k, v) for k, v in form.item_price()]))
        order_obj['invoice_hash'] = str(uuid.uuid4()).split("-")[0]
        order_obj["url"] = "https://elegansvariation.org/order/" + order_obj["invoice_hash"]
        send_email({"from": "no-reply@elegansvariation.org",
                    "to": [order_obj["email"]],
                    "cc": config.get("CC_EMAILS"),
                    "subject": "CeNDR Order #" + str(order_obj["invoice_hash"]),
                    "text": ORDER_SUBMISSION_EMAIL.format(**order_obj)})

        # Save to google sheet
        add_to_order_ws(order_obj)
        flash("Thank you for submitting your order! Please follow the instructions below to complete your order.", 'success')
        return redirect(url_for("order.order_confirmation", invoice_hash=order_obj['invoice_hash']), code=302)
    return render_template('order/order.html', **locals())


@order_bp.route("/invoice/<invoice_hash>/", methods=['GET', 'POST'])
def order_confirmation(invoice_hash):
    order_obj = lookup_order(invoice_hash)
    if order_obj:
        order_obj["items"] = {x.split(":")[0]: float(x.split(":")[1])
                              for x in order_obj['items'].split("\n")}
        if order_obj is None:
            abort(404)
        title = f"Invoice {order_obj['invoice_hash']}"
        return render_template('order/order_confirm.html', **locals())
    else:
        abort(404)
