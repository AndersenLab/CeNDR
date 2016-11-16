import sys
sys.path.append("lib")
print sys.path


import pip
installed_packages = pip.get_installed_distributions()
installed_packages_list = sorted(["%s==%s" % (i.key, i.version)
     for i in installed_packages])
print(installed_packages_list)

# Add any libraries installed in the "lib" folder.
from cendr.views.api import *


def test_one():
    assert 1 == 1