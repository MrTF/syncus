#!/usr/bin/env python
#
# Copyright 2009 (C) Fatih Tumen
# fthtmn _eta_ googlemail _dot_ com
#
# This file is a part of Smart Synchroniser Project
# Smart Synchroniser Installer
# setup.py 
#
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 2 of the License, or
# version 3 of the License, or (at your option) any later version. It is
# provided for educational purposes and is distributed in the hope that
# it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
# the GNU General Public License for more details.
#

import os
import sys
import glob
import shutil

version = "0.1"

distfiles = """
    README
    *.py
    *.desktop
    data/
"""

def make_dist():
    distdir = "smart-synchroniser-%s" % version
    list = []
    for t in distfiles.split():
        list.extend(glob.glob(t))
    if os.path.exists(distdir):
        shutil.rmtree(distdir)
    os.mkdir(distdir)
    for file_ in list:
        cum = distdir[:]
        for d in os.path.dirname(file_).split('/'):
            dn = os.path.join(cum, d)
            cum = dn[:]
            if not os.path.exists(dn):
                os.mkdir(dn)
        shutil.copy(file_, os.path.join(distdir, file_))
    os.popen("tar -czf %s %s" % ("smart-synchroniser-" + version + ".tar.gz", distdir))
    shutil.rmtree(distdir)

if "dist" in sys.argv:
    make_dist()
    sys.exit(0)

app_data = [
    ('/usr/local/smart-synchroniser/', ['smartsync.desktop', 'smartsync.py',  'smartcompare.py', 'ui_smartsyncdlg.py', 'smb.py', 'nmb.py', 'smbcp.py'],),
	('/usr/local/smart-synchroniser/data/', ['data/reload_32.png', 'data/empty.png','data/folder.png','data/reload.png',],),]

]

attrs = {
    'name' : "Smart Synchroniser",
    'version' : version,
    'author' : "Fatih Tümen",
    'author_email' : "fthtmn@googlemail.com",
    #'url' : "",
    'license' : "GNU GPL v2",
    #'scripts' : use_scripts,
    #'packages' : [],
    #'package_dir' : {"": ""},
    #'package_data' : {"BTL": ["*.dat"]},
    #'py_modules' : ["Zeroconf",],
    'data_files' : data_files,
    'description' : "Bidirectional Directory Synchronisation Tool",
    'long_description' : """
	""",
}

setup(**attrs)
