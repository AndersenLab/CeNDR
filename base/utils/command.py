import click
from flask import Flask

from base.application import app

@app.cli.command()
def initdb():
    """Initialize the database."""
    click.echo('Init the db')