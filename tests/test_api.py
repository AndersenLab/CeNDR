import sys
print sys.path

import glob
print glob.glob("*")
print glob.glob("lib/*")


from cendr.views.api import *


def test_one():
    assert 1 == 1