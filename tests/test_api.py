import sys
sys.path.append("/home/travis/build/AndersenLab/CeNDR/lib/")
print sys.path

import glob
print glob.glob("/home/travis/build/AndersenLab/CeNDR/lib/google/*")

import pip
installed_packages = pip.get_installed_distributions()
installed_packages_list = sorted(["%s==%s" % (i.key, i.version)
     for i in installed_packages])
print(installed_packages_list)

print(pip.get_installed_distributions())

# Add any libraries installed in the "lib" folder.
from cendr.views.api import *


def test_one():
    assert 1 == 1