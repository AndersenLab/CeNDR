import sys
print sys.path

from cendr.views.api import *


def test_one():
    assert 1 == 1