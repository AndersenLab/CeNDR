import os
from base.application import create_app
from logzero import logging

# Initialize application
app = create_app()
print(app)