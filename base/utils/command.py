import click
import requests
from flask import Flask
import sqlite3
from base.utils.google_sheets import get_google_sheet

conn = sqlite3.connect("flights.db")

from base.application import app

@app.cli.command()
def initdb():
    """Initialize the strain database."""
    click.echo('Init the db')
    WI = get_google_sheet("WI")
    strain_records = WI.get_all_records()
