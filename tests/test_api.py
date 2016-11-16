import sys
print sys.path

import glob
print glob.glob("*")
print glob.glob("lib/*")
print glob.glob("lib/*")

from google.appengine.ext import vendor
import os

# Add any libraries installed in the "lib" folder.
vendor.add(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))
from cendr.views.api import *


def test_one():
    assert 1 == 1