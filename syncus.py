#!/usr/bin/env python
#
# Copyright 2009 Fatih Tumen
# fthtmn _eta_ googlemail.com
#
# This file is a part of Smart Synchroniser Project
# Smart Synchroniser Main
# smartsync.py 
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

__version__ = "$Revision: 30 $"

import time
global launch_time
launch_time = time.time()

import os
import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import commands
from subprocess import call
from pysmb import nmb, smb
import tempfile

import ui_smartsyncdlg as Ui_smartsyncdlg
import ui_progressdlg
import smartcompare as sc
from smartsync import SmartSync


class Syncus(QMainWindow, 
                Ui_smartsyncdlg.Ui_smartsyncdlg):
    
    def __init__(self, parent = None, leftdir=None, rightdir=None, verbose=False):
        
        super(Syncus, self).__init__(parent)
        self.setupUi(self)
        self.lock = QReadWriteLock()
        
        settings = QSettings()
        self.restoreGeometry(settings.value("Geometry").toByteArray())
        self.unidir = self.unidirCheckBox.isChecked()

        if leftdir and rightdir:
            self.leftComboBox.addItem(os.path.expanduser(leftdir))
            self.rightComboBox.addItem(os.path.expanduser(rightdir))
        else:
            self.leftComboBox.addItem(os.path.expanduser("~/"))
            self.rightComboBox.addItem(os.path.expanduser("~/"))


        #list of items that will be excluded from comparison
        #self.ignored = [unicode(all) for all in self.excludedItems.itervalues()]
        self.excludedItemsList = {}
        self.ignored = []
        self.trash = None
        self.verbose = verbose
        
        #TODO:
        #self.LoadProfile()
        
        self.statusbar.showMessage("[%.3fs] Ready"%(time.time() - launch_time))
        self.control = 0
        
        
    def Sanity(self):
        """This method is first invoked when "compare pushbutton is clicked.
        It will do some some initial sanity checks and inits before passing the 
        job to self.Compare()
        """
        
        self.l2rJobQueue = {}
        self.r2lJobQueue = {}
        self.LN = False
        self.RN = False
        
        #CHECK: if unicode conversion is OK for multilingual names?
        lpath = unicode(self.leftComboBox.currentText())
        rpath = unicode(self.rightComboBox.currentText())
        
        assert lpath != '', unicode("Left directory path is empty!")
        assert rpath != '', unicode("Right directory path is empty!")
        
        #real paths (without filters) will be locally referred as 
        #locally: left_path and right_path 
        #globally: self.left_path and self.right_path  
        #we keep the original input for historical reasons
        
        #we don't give a gui option for hidden items since 
        #it does not make much sense for the user but we
        #hide current and parent dirs by default; this is not a browser!
        self.hidden = [os.curdir, os.pardir]

        #if filter is used in the directory paths (i.e: /home/user/images/DSC*.jpg) 
        #we will add every file, that does not match with the filter, to the ignored list.
        #CHECK:  whether it works if dir/file name contains literal asterisk *
        #FIXME: filter needs base name but we give full path!!
        filter = self.isFilter(L=lpath, R=rpath)    
        if filter:
            lpath = lpath.rstrip(filter)
            rpath = rpath.rstrip(filter)
            
        #If the given paths are network paths pass them to NWHandler
        #if they are local paths direcly check whether they are real
        if lpath.startswith(("smb://","//","\\\\")):
            LN = True
            self.RNP = lpath
            lpath = self.NWHandler(lpath, side='r2l')
            assert lpath != None, unicode("Error 12: Unknown network error occurred!")            
        else:
            assert os.path.isdir(lpath), unicode("%s: No such directory" % lpath) 
            lpath = os.path.expandvars(lpath)
            lpath = os.path.expanduser(lpath)        
            lpath = os.path.join(lpath)
            
        if rpath.startswith(("smb://","//","\\\\")):
            assert self.LN == False, unicode("We do not support remote <=> remote synchronisation")
            self.RN = True
            self.RNP = rpath
            rpath = self.NWHandler(rpath, side='r2l')
            assert rpath != None, unicode("[Error 12]: Unknown network error occurred!")
            
        else:
            assert os.path.isdir(rpath), unicode("%s: No such directory" % rpath)
            rpath = os.path.expandvars(rpath)            
            rpath = os.path.expanduser(rpath)
#            rpath = os.path.realpath(rpath)
#            rpath = os.path.dirname(rpath)
            rpath = os.path.join(rpath)        

        self.left_path = lpath
        self.right_path = rpath
        #usage of more than one joker character is confusing; keep it simple!
        if filter:
            filter = filter.split('*')                
            self.Filter(head=filter[0], tail=filter[1])
 
        if self.hiddenCheckBox.isChecked():
            self.Filter(head='.', tail='', exclude=True)
            
        return lpath, rpath
        
        
    def Compare(self, source, destination):
        '''This function is invoked when the "Compare" button on "Main" view is
        clicked. It will compare left and right directories and populate the 
        QTreeWidgets with comparison results'''

        #Compare directories
        self.left_path = source
        left_path = source
        self.right_path = destination
        right_path = destination
        
        self.result = sc.dircmp(self.left_path, 
                                self.right_path,
                                ignore=self.ignored,
                                hide=self.hidden,
                                shallow=(not self.contentCheckBox.isChecked())
                                )

        self.result.report_full_closure()
        self.everything = self.result.everything()
        #FIXME: FIXED? report_full_closure() does not seem to be recursing everytime

        #Populate tree widgets
        
        #TODO: Get icons either from system or ../data folder
        #folder_icon = '/usr/share/icons/kdeclassic/32x32/places/folder.png'
        #file_icon = '/usr/share/icons/kdeclassic/32x32/mimetypes/empty.png'
        folder_icon = 'data/folder.png'
        file_icon = 'data/empty.png'
        self.leftTreeWidget.clear()
        self.leftTreeWidget.setItemsExpandable(True)        
        ancestor = None        
        self.leftAncestors = {}
        self.leftItems = {}
        self.leftItemCount = 0
        self.leftTotalSize = 0
        self.leftSizeUnit = ''
        
        #TODO: use a method, self.PopulateTree, instead repetetive code below
        # and put each populate action in a secondary thread 

        for root, dirs, files in os.walk(left_path):
            if root == left_path:
                for _dir in dirs:
                    _path = os.path.join(root, _dir)
                    if _path in self.everything.keys(): 
                        color = self.Colorise(_path)  #[color, tooltip]                        
                        _item = self.Itemise(_path)
                        ancestor = QTreeWidgetItem(self.leftTreeWidget, _item)
                        icon = QIcon()
                        icon.addPixmap(QPixmap(folder_icon), QIcon.Normal, QIcon.On)
                        ancestor.setIcon(0, icon)
                        ancestor.setTextColor(0, color[0])
                        ancestor.setToolTip(0, color[1]%("directory", "right"))
                        self.leftAncestors[_path] = ancestor
                        self.leftItems[ancestor] = _path
                        self.Stat('left', _item)
                for _file in files:
                    _path = os.path.join(root, _file)
                    if _path in self.everything.keys():
                        color = self.Colorise(_path)
                        _item = self.Itemise(_path) #[name, size, date]
                        item = QTreeWidgetItem(self.leftTreeWidget, _item)
                        icon = QIcon()
                        icon.addPixmap(QPixmap(file_icon), QIcon.Normal, QIcon.On)
                        item.setIcon(0, icon)
                        item.setTextColor(0, color[0])
                        item.setToolTip(0, color[1]%("file", "right"))
                        self.leftItems[item] = _path
                        self.Stat('left', _item)
            
            if root != left_path and self.recursiveCheckBox.isChecked():
                for _dir in dirs:
                    _path = os.path.join(root, _dir)
                    if _path in self.everything.keys():
                        color = self.Colorise(_path)
                        _item = self.Itemise(_path)
                        ancestor = self.leftAncestors.get(root)
                        ancestor = QTreeWidgetItem(ancestor, _item)
                        icon = QIcon()
                        icon.addPixmap(QPixmap(folder_icon), QIcon.Normal, QIcon.On)
                        ancestor.setIcon(0, icon)
                        ancestor.setTextColor(0, color[0])
                        ancestor.setToolTip(0, color[1]%("directory", "right"))
                        self.leftAncestors[_path] = ancestor
                        self.leftItems[ancestor] = _path
                        self.Stat('left', _item)
                for _file in files:
                    _path = os.path.join(root, _file)
                    if _path in self.everything.keys():
                        color = self.Colorise(_path)
                        _item = self.Itemise(_path)
                        ancestor = self.leftAncestors.get(root)
                        item = QTreeWidgetItem(ancestor, _item)
                        icon = QIcon()
                        icon.addPixmap(QPixmap(file_icon), QIcon.Normal, QIcon.On)
                        item.setIcon(0, icon)
                        item.setTextColor(0, color[0])
                        item.setToolTip(0, color[1]%("file", "right"))
                        self.leftItems[item] = _path
                        self.Stat('left', _item)
        
        self.leftTreeWidget.expandAll()
        for y in xrange(3):
            self.leftTreeWidget.resizeColumnToContents(y)        

#        self.leftTreeWidget.sortByColumn(0)
        self.leftBottomLabel.setText("<font color='darkCyan'>Scan result:</font> <b>%i items</b> with total size of <b>%.1f%s</b>"
                                      %(self.leftItemCount, 
                                        self.leftTotalSize,
                                        self.leftSizeUnit))
        
        #we need a dictionary of paths:items as well as items:paths.
        #instead having it intermediately after each self.*items[item] = path
        #we generate one by swapping the keys:values of the self.*Items
        self.leftPaths  = {}
        for v, k in self.leftItems.iteritems():
              self.leftPaths[k] = v
        
        #rightTreeWidget joins the party here
  
        self.rightTreeWidget.clear()
        self.rightTreeWidget.setItemsExpandable(True)
        ancestor = None
        self.rightAncestors = {}
        self.rightItems = {}
        self.rightItemCount = 0
        self.rightTotalSize = 0
        self.rightSizeUnit = ''

        for root, dirs, files in os.walk(right_path):
            if root == right_path:
                for _dir in dirs:
                    _path = os.path.join(root, _dir)
                    if _path in self.everything.keys():
                        color = self.Colorise(_path)
                        _item = self.Itemise(_path)
                        ancestor = QTreeWidgetItem(self.rightTreeWidget, _item)
                        icon = QIcon()
                        icon.addPixmap(QPixmap(folder_icon), QIcon.Normal, QIcon.On)
                        ancestor.setIcon(0, icon)
                        ancestor.setTextColor(0, color[0])
                        ancestor.setToolTip(0, color[1]%("directory", "left"))
                        self.rightAncestors[_path] = ancestor
                        self.rightItems[ancestor] = _path
                        self.Stat('right', _item)
                        
                for _file in files:
                    _path = os.path.join(root, _file)
                    if _path in self.everything.keys():
                        color = self.Colorise(_path)
                        _item = self.Itemise(_path)
                        item = QTreeWidgetItem(self.rightTreeWidget, _item) 
                        icon = QIcon()
                        icon.addPixmap(QPixmap(file_icon), QIcon.Normal, QIcon.On)
                        item.setIcon(0, icon)
                        item.setTextColor(0, color[0])
                        item.setToolTip(0, color[1]%("file", "left"))
                        self.rightItems[item] = _path
                        self.Stat('right', _item)
                        
            if root != right_path and self.recursiveCheckBox.isChecked():
                for _dir in dirs:
                    _path = os.path.join(root, _dir)
                    if _path in self.everything.keys():
                        color = self.Colorise(_path)
                        _item = self.Itemise(_path)
                        ancestor = self.rightAncestors.get(root)
                        ancestor = QTreeWidgetItem(ancestor, _item)
                        icon = QIcon()
                        icon.addPixmap(QPixmap(folder_icon), QIcon.Normal, QIcon.On)
                        ancestor.setIcon(0, icon)
                        ancestor.setTextColor(0, color[0])
                        ancestor.setToolTip(0, color[1]%("directory", "left"))
                        self.rightAncestors[_path] = ancestor
                        self.rightItems[ancestor] = _path
                        self.Stat('right', _item)
                for _file in files:
                    _path = os.path.join(root, _file)
                    if _path in self.everything.keys():
                        color = self.Colorise(_path)
                        _item = self.Itemise(_path)
                        ancestor = self.rightAncestors.get(root)
                        item = QTreeWidgetItem(ancestor, _item)
                        icon = QIcon()
                        icon.addPixmap(QPixmap(file_icon), QIcon.Normal, QIcon.On)
                        item.setIcon(0, icon)
                        item.setTextColor(0, color[0])
                        item.setToolTip(0, color[1]%("file", "left"))
                        self.rightItems[item] = _path
                        self.Stat('right', _item)
                        
        self.rightTreeWidget.expandAll()
        for y in xrange(3):
            self.rightTreeWidget.resizeColumnToContents(y)

#        self.rightTreeWidget.sortByColumn(0)
        self.rightBottomLabel.setText("<font color='darkCyan'>Scan result:</font> <b>%i items</b> with total size of <b>%.1f%s</b>"
                                      %(self.rightItemCount, 
                                        self.rightTotalSize,
                                        self.rightSizeUnit))
        
        #likewise self.leftPaths above
        self.rightPaths  = {}
        for v, k in self.rightItems.iteritems():
              self.rightPaths[k] = v
        
        #Upon successful comparison add paths to history                
        self.leftComboBox.addItem(left_path)
        self.rightComboBox.addItem(right_path)
        

    def isFilter(self, L=None, R=None, single=None):
        '''If the given string matches our filter pattern it returns 
        head and tail of the filter, else None.
        '''
        
        filter = None
        if not ((L and R) or single): 
            return None
        
        if single:
            single_filter = os.path.basename(single)
            if not single_filter.count('*'):
                return None
            else:
                assert single_filter.count('*') == 1 ,unicode("%s: Invalid filter pattern\n\
                Only one joker character is supported in the filter pattern." % single)
                filter = single_filter
                 
        left_filter = os.path.basename(L)
        right_filter = os.path.basename(R)
        if left_filter.count('*') and right_filter.count('*'):
            #if filter is used in both paths they must be same
            assert left_filter == right_filter, unicode("Ambiguous usage of filters in directory paths!")
        elif left_filter.count('*'):
            filter = left_filter
        elif right_filter.count('*'):
            filter = right_filter
        
        if filter:
            return filter
    
    #FIXME: filter takes base name but we give absolute path     
    def Filter(self, head=None, tail=None, exclude=False):
        '''This method is invoked:
        0\ by self.Compare without exclude when 
            01\ filter is used in the directory path(s).
            02\ "Ignore hidden items" option is checked.
        1\ by self.PopulateExcludedList with exclude when:             
            10\ "Add" button in excludeGroup is clicked.
            11\ "Remove" button is excludeGroup is clicked.
            
        without exclude It will add every _file_ not starting with head and 
        not ending with tail to the ignored list.  
        with exculde it will to add every file _and_ directory to the ignored list. 
        ''' 

        if exclude:
            excludeds = []

        for root, dirs, files in os.walk(self.left_path):
            if self.recursiveCheckBox.isChecked() and root != self.right_path:
                break
            for name in files:
                if exclude:
                    if head != '' and name.startswith(head):
                        excludeds.append(name)
                        
                    if tail != '' and name.endswith(tail):
                        excludeds.append(name)
                else:
                    if head != '' and not name.startswith(head):
                        self.ignored.append(name)
                    if tail != '' and not name.endswith(tail):
                        self.ignored.append(name)
            if exclude:
                for name in dirs: 
                    if head != '' and name.startswith(head):
                        excludeds.append(name)
                    if tail != '' and name.endswith(tail):
                        excludeds.append(name)

        for root, dirs, files in os.walk(self.right_path):            
            if self.recursiveCheckBox.isChecked() and root != self.right_path:
                break
            for name in files:
                if exclude:
                    if head != '' and name.startswith(head):
                        excludeds.append(name)
                    if tail != '' and name.endswith(tail):
                        excludeds.append(name)
                else:
                    if head != '' and not name.startswith(head):
                        self.ignored.append(name)
                    if tail != '' and not name.endswith(tail):
                        self.ignored.append(name)
            if exclude:
                for name in dirs:
                    if head != '' and name.startswith(head):
                        excludeds.append(name)
                    if tail != '' and name.endswith(tail):
                        excludeds.append(name)
                        
        if exclude:
            for i in excludeds:
                if i in self.ignored:
                    excludeds.pop(excluded.index(i))
            self.excludedItemsList[head + '*' + tail] = excludeds
            self.ignored.extend(excludeds)
            del excludeds

    def NWHandler(self, remote, local=None, side=None):
        """This method is invoked by sanity whenever we have a network path 
        """
        #TODO: (1) Maybe this function should never return and not give control to Compare() ?
        #        HOWTO: In the pushbutton caller we can check for True/False return value of Sanity 
        #             and call Compare accordingly
        #            (2) Alternatively improve smartcompare.py to handle networks?

        if local:
            destination = local

        if side == "r2l" and local is None:
            destination = self.trash = tempfile.mkdtemp(prefix="SS-") + "/"

        if remote.startswith("smb://") or "//":
            self.dl = "/"
        else:
            self.dl = "\\\\"

        remotes = remote.split(self.dl)
        assert len(remotes) > 1, unicode("Invalid remote address!\n%"%remote)
        hostname, dir = remotes[2], remotes[3]
        assert len(hostname.split('.')) == 1, unicode("Remote host name is required!\nUsage of IP is currently not supported.")
        
        source = 'nmb@%s:/%s/' %(hostname, dir)
        if side == 'l2r':
            tmp = destination
            destination = source
            source = tmp
        
        try:
            #print "Calling:", ['python', 'smbcp', '-r', '%s'%source, '%s/'%destination]
            cached = call(['python', 'smbcp', '-r', '%s'%source, '%s/'%destination])
            if side == 'r2l':
                return destination
            return True
        except:
            raise Exception("Network Error")
        
        return None

                    
    def NWBrowser(self, sock, parent, fil,  t=""):
        #try:
#        N = nmb.NetBIOS()
#        address = N.gethostbyname(name)[0]
#        ip, host = address.get_ip(), address.get_nbname()
#        remote = smb.SMB(host, ip)
#        remote.login('','')
#        sock.list_path(_dir, "*")
        
        #except:
        #self.NWBrowser(_sock, _path, "*")

        for i in sock.list_path(parent, "*"):
            name = i.get_longname()
            #print t, name
            if i.is_directory():            
                try:
                    self.NWBrowser(sock, parent + self.dl + name, "*", t='\t')
                except:
                    continue
                
    

    def Itemise(self, _path ):
        '''This function is called by self.Compare() while populating tree 
        widgets.It will return column elements of the item in a row:
        [name, size, date]'''
        
        name = _path.split('/')[-1]
        # TODO: Better use os.stat.msize for size?
        size = commands.getoutput('du -hs "%s"'%_path).split('/')[0].replace('\t','')
        date = commands.getoutput('stat --format=%%y "%s"'%_path).split(' ')
        date = date[0] + ' ' + date[1].split('.')[0]

        return [name, size, date]
    
    #FIXME: if necessary use left_lessrecent and right_lessrecent labels 
        
    def Colorise(self, name):        
        '''This function is called by self.Compare() while populating tree 
        widgets. It returns the color of the row and its tooltip according 
        to comparison results self.result
        This is also a good place to initiliase our job queues for self.Sync() '''
        
        if name.startswith(self.left_path):
            jobList = self.l2rJobQueue
            source_base = self.left_path
            dest_base = self.right_path
        else:
            jobList = self.r2lJobQueue
            source_base = self.right_path
            dest_base = self.left_path

        color = None
        V = self.everything.get(name)
        #TODO: replace(source_base, dest_base) to color *_recent items red on the other side     
        if V in ['left_only', 'right_only', ]:
            color = Qt.blue
            tooltip = "This %s is found only in this directory, will be copied to %s directory."
            jobList[name] = name.replace(source_base, dest_base)
        elif V in ['funny_files', 'common_funny']:
            color = Qt.gray
            tooltip = "This %s could not be compared.%s"
        elif V in ['same_files', 'common_dirs']:
            color = Qt.black
            tooltip = "This %s is identical with the one on the %s directory"
        elif V in ['left_recent', 'right_recent']:
            color = Qt.darkBlue
            tooltip = "This %s is more recent, will be copied to %s directory"
            jobList[name] = name.replace(source_base, dest_base)
        else:
            color = Qt.red
            tooltip = "This %s will be overwritten with the one on the %s directory"
            jobList[name] = name.replace(source_base, dest_base)
                        
        if os.path.isdir(V):
            color = Qt.black
            
        if name.startswith(self.left_path):
            self.l2rJobQueue = jobList
        else:
            self.r2lJobQueue = jobList

        if color:
            return [color, tooltip]
        else:   #we should never get here.
            #print "name: ", name
            return [Qt.magenta, "Unknown state of the space shuttle"]
    
    def Stat(self, side, item):
        '''This function is called by self.Compare while populating tree widget,
        to keep track of the total number of items and total size of them.
        '''
        #TODO: This is the most primitive method ever, find a better one!
        
        total = 0 
        size = item[1]
        K, M, G = False, False, False          
              
        if size[-1] == 'K': 
            total += float(size[:-1]); K=True   #default is K
        elif size[-1] == 'M': 
            total += float(size[:-1]) / 1024; M=True 
        elif size[-1] == 'G': 
            total += float(size[:-1]) / 1024 / 1024; G=True
        else: 
            total += float(size[:-1]) * 1024
        if G: 
            total = total * 1024 * 1024; su='G'
        elif M: 
            total = total * 1024; su='M'
        elif K: 
            total = total; su='K'
        else: 
            total = total * 1024; su=''

        if side == 'left':
            self.leftItemCount += 1
            self.leftTotalSize += total
            self.leftSizeUnit = su 
        else:
            self.rightItemCount += 1
            self.rightTotalSize += total
            self.rightSizeUnit = su
    
    
    def Sync(self):
        '''This method is invoked when the "Synchronise" button is click.
        It will process the job queues prepared by self.Compare.
        '''
        #TODO: put both l2r and r2l jobs in a seperate thread 
        # and use progress dialog 
        
        if self.unidir and (self.l2rJobQueue == 0 or len(self.r2lJobQueue) == 0):
            QMessageBox.warning(self, "Sync Error", unicode("There is nothing to synchronise!"))
            return False       
        elif len(self.l2rJobQueue) == 0 and len(self.r2lJobQueue) == 0:
            QMessageBox.warning(self, "Sync Error", unicode("There is nothing to synchronise!"))
            return False
        
#        import ui_progressdlg
#        progress = ui_progressdlg.Ui_progressdlg()
#        
        
        
        args = []
        if self.verbose:
            args.append('-v')
        args.append('--force')
        args.append('--recursive')
        if self.backupCheckBox.isChecked():
            args.append('--backup=numbered')
        if self.ownershipCheckBox.isChecked():
            args.append('--preserve=ownership')
        else:
            args.append('--no-preserve=ownership')
        if self.permissionsCheckBox.isChecked():
            args.append('--preserve=mode')
        else:
            args.append('--no-preserve=mode')
        if self.timestampsCheckBox.isChecked():
            args.append('--preserve=timestamps')
        else:
            args.append('--no-preserve=timestamps')

        
        self.progress = QDialog()
        self.progressdlg = ui_progressdlg.Ui_progressdlg(self)
        self.progressdlg.setupUi(self.progress)
        
        self.syncer = SmartSync(self.lock,  self)
        self.connect(self.syncer,  SIGNAL("syncing()"),  self.Syncing)
        self.connect(self.syncer,  SIGNAL("finished(bool)"),  self.Synced)
        
        self.leftTotal = len(self.l2rJobQueue)
        self.rightTotal = len(self.r2lJobQueue)
        
        self.syncer.initialize(self.unidir, 
                               self.l2rRadioButton.isChecked(), 
                               self.r2lRadioButton.isChecked(), 
                               self.l2rJobQueue.iteritems(),  
                               self.r2lJobQueue.iteritems(),  
                               args
                               )
                               
        self.progress.show()                   
        #self.connect(self.progress, SIGNAL("accept()"),  self.syncer.start)
        self.connect(self.progressdlg.buttonBox, SIGNAL("accepted()"), self.syncer.start)
        #self.syncer.start()
        
#        self.l2rJobQueue = {}
#        self.r2lJobQueue = {}


    def Syncing(self):
        with QReadLocker(self.lock):
            leftP = len(self.l2rJobQueue) * 100 / self.leftTotal
            rightP = len(self.r2lJobQueue) * 100 / self.rightTotal
            
        self.progressdlg.Progress(leftP,  rightP)
        
    def Synced(self,  isSynced):
        self.isSynced = isSynced
        return isSynced

    def PopulateExcludeList(self, excludeList=None):
        self.excludeListWidget.clear()
        self.excludeListItems = {}
        for each in self.excludedItemsList.iterkeys():            
            item = QListWidgetItem(each)
            self.excludeListWidget.addItem(item)
            self.excludeListItems[item] = each
        if len(self.excludeListItems) != 0:
            self.removePushButton.setEnabled(True)    


    def updateStatus(self, message):
        self.statusBar().showMessage(message)


    def on_leftOpenButton_clicked(self):
        currentDir = self.leftComboBox.currentText()
        dir = QFileDialog.getExistingDirectory(self, unicode("Choose left directory..."), currentDir,
                                               (QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks))
        if dir != '':
            self.leftComboBox.setEditText(dir + '/')

    
    #FIXME: FIXED? setSelected() for 3middle buttons does not work as it should be
    #TODO: label the parent and child items with respect to each other    


    def on_l2rPushButton_clicked(self):
        selected = None
        for selected in self.leftTreeWidget.selectedItems():
            selected.setTextColor(0, Qt.blue)
            selected.setToolTip(0, "This item will be copied to right directory")   
            source = self.leftItems[selected]   
            destination = source.replace(self.left_path, self.right_path)
            self.l2rJobQueue[source] = destination
            destItem = self.rightPaths.get(destination)
            if destItem:
                destItem.setTextColor(0, Qt.red)
                destItem.setToolTip(0, "This item will be overwritten")
            if self.r2lJobQueue.get(destination): 
                del self.r2lJobQueue[destination]

        if selected:
            nextItem = self.leftTreeWidget.itemBelow(selected)
            self.leftTreeWidget.clearSelection()
            self.leftTreeWidget.setItemSelected(nextItem, True)

    def on_eqPushButton_clicked(self):
          
        selected = None
        for selected in self.leftTreeWidget.selectedItems():
            selected.setTextColor(0, Qt.black)
            selected.setToolTip(0, "This item is identical with the one on the other side????")   
            source = self.leftItems[selected]   
            destination = source.replace(self.left_path, self.right_path)
            if self.l2rJobQueue.get(source):
                del self.l2rJobQueue[source]
            if self.r2lJobQueue.get(destination): 
                del self.r2lJobQueue[destination]  
            destItem = self.rightPaths.get(destination)
            if destItem:
                destItem.setTextColor(0, Qt.black)
                selected.setToolTip(0, "No action will be taking on this item")                        

        if selected:
            nextItem = self.leftTreeWidget.itemBelow(selected)
            self.leftTreeWidget.clearSelection()
            self.leftTreeWidget.setItemSelected(nextItem, True)  
            
        selected = None
        for selected in self.rightTreeWidget.selectedItems():
            #print "selected", selected
            selected.setTextColor(0, Qt.black)
            selected.setToolTip(0, "No action will be taking on this item")   
            source = self.rightItems[selected]   
            destination = source.replace(self.right_path, self.left_path)
            if self.r2lJobQueue.get(source):
                del self.r2lJobQueue[source]
            if self.l2rJobQueue.get(destination): 
                del self.l2rJobQueue[destination]  
            destItem = self.leftPaths.get(destination)
            if destItem:
                destItem.setTextColor(0, Qt.black)
                selected.setToolTip(0, "No action will be taking on this item")                        

        if selected:
            nextItem = self.rightTreeWidget.itemBelow(selected)
            self.rightTreeWidget.clearSelection()
            self.rightTreeWidget.setItemSelected(nextItem, True)
          
    def on_r2lPushButton_clicked(self):
        selected = None
        for selected in self.rightTreeWidget.selectedItems():
            selected.setTextColor(0, Qt.blue)
            selected.setToolTip(0, "This item will be copied to left directory")   
            source = self.rightItems[selected]
            destination = source.replace(self.right_path, self.left_path)
            self.r2lJobQueue[source] = destination
            destItem = self.leftPaths.get(destination)            
            if destItem:
                destItem.setTextColor(0, Qt.red)
                selected.setToolTip(0, "This item will be overwritten")
            if self.l2rJobQueue.get(destination): 
                del self.l2rJobQueue[destination]
                
        if selected:
            nextItem = self.rightTreeWidget.itemBelow(selected)
            self.rightTreeWidget.clearSelection()
            self.rightTreeWidget.setItemSelected(nextItem, True)
        

    def on_rightOpenButton_clicked(self):
        currentDir = self.rightComboBox.currentText()
        dir = QFileDialog.getExistingDirectory(self, unicode("Choose right directory..."), currentDir,
                                               (QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks))
        if dir != '':
            self.rightComboBox.setEditText(dir + '/')

    
    @pyqtSignature("")
    def on_unidirCheckBox_clicked(self):
        self.unidir = self.unidirCheckBox.isChecked()
        if self.unidir:
            if self.l2rRadioButton.isChecked():
                self.on_l2rRadioButton_clicked()
            elif self.r2lRadioButton.isChecked():
                self.on_r2lRadioButton_clicked()
            self.l2rRadioButton.setEnabled(True)
            self.r2lRadioButton.setEnabled(True)           
        else:
            self.l2rRadioButton.setEnabled(False)
            self.r2lRadioButton.setEnabled(False)
            self.l2rPushButton.setEnabled(True)
            self.r2lPushButton.setEnabled(True)
        
    
    @pyqtSignature("")
    def on_l2rRadioButton_clicked(self):
        self.l2rPushButton.setEnabled(True)
        self.r2lPushButton.setEnabled(False)
        
    
    @pyqtSignature("")
    def on_r2lRadioButton_clicked(self):
        self.l2rPushButton.setEnabled(False)
        self.r2lPushButton.setEnabled(True)

    @pyqtSignature("QString")
    def on_excludeLineEdit_textEdited(self):        
        self.addPushButton.setEnabled(True)
        

    @pyqtSignature("")
    def on_excludeLineEdit_returnPressed(self):
        self.on_addPushButton_clicked()

    
    @pyqtSignature("")
    def on_excludeOpenButton_pressed(self):
        excludeDialog = QFileDialog()
        excludeDialog.setFileMode(QFileDialog.AnyFile)
        item = excludeDialog.getOpenFileName(self, unicode("Choose an item to exclude..."),
                                                 self.excludeLineEdit.text())
        if item != '':
            self.excludeLineEdit.clear()
            self.excludeLineEdit.insert(item)
    
    
    @pyqtSignature("")
    def on_addPushButton_clicked(self):
        text = self.excludeLineEdit.text().trimmed()
        if text.isEmpty():
            #raise warning?
            return 
        
        text = unicode(self.excludeLineEdit.text())
        self.excludeLineEdit.clear()
        if text in self.excludedItemsList.iterkeys():
            #raise warning?
            return
        
        #if user entered filter let self.Filter take care of it
        filter = self.isFilter(single=text)
        if filter:
            filter = filter.split('*')      
            self.Filter(head=filter[0], tail=filter[1], exclude=True)
        else:
            #otherwise simply add it 
            self.ignored.append(text)
            #and keep up the uniform structure of {pattern:[matchin path(s)]}
            self.excludedItemsList[text] = [text]
            
        self.PopulateExcludeList()

    
    @pyqtSignature("")
    def on_removePushButton_pressed(self):
        item = self.excludeListWidget.currentItem()
        if item is None:
            return
        text = self.excludeListItems[item]
        for _path in self.excludedItemsList[text]:
            self.ignored.pop(self.ignored.index(_path))
        del self.excludedItemsList[text]
        
        self.PopulateExcludeList()
    
    @pyqtSignature("")
    def on_comparePushButton_pressed(self):
        start_time = time.time()
        self.leftBottomLabel.setText("")
        self.rightBottomLabel.setText("")
        self.updateStatus("Comparing directories...")
        try:
            lpath, rpath = self.Sanity()
            self.Compare(lpath, rpath)
            self.updateStatus("[%.3fs] Compared directories"%(time.time() - start_time))
        except AssertionError, why:
            self.leftBottomLabel.setText("")
            self.rightBottomLabel.setText("")
            self.updateStatus("[%.3fs] Compare failed!"%(time.time() - start_time))
            QMessageBox.critical(self, unicode("SmartSync - AssertionError"), unicode(why))
        except Exception:
            self.leftBottomLabel.setText("")
            self.rightBottomLabel.setText("")
            self.updateStatus("[%.3fs] Compare failed!"%(time.time() - start_time))
##            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
##            QMessageBox.critical(self, unicode("Oops! - SmartSync"), 
##                                 unicode("Comparison could not be completed.\n\
##Please report this issue to the developer with the following information:\n\n\
##%s\n%s\n%s:%i" %(exceptionType, exceptionValue,
##                    exceptionTraceback.tb_frame.f_back.f_code.co_filename,
##                    exceptionTraceback.tb_lineno)))


    @pyqtSignature("")
    def on_syncPushButton_pressed(self):
        start_time = time.time()
        self.statusbar.showMessage("Synchronising...")
        try:
            if self.Sync() and self.isSynced:
                
                fin = True
                if self.LN:
                    #print "LN: copying from %s to %s" %(self.left_path, self.LNP)
                    fin = self.NWHandler(self.left_path, self.LNP, side='l2r')
                    #print self.LN, self.left_path, self.LNP
                elif self.RN:
                    #print "RN: copying from %s to %s"%(self.right_path, self.RNP)
                    fin = self.NWHandler(self.right_path, self.RNP, side='l2r')
                if not fin:
                    raise smb.SessionError("E: Unknown network error occured.")
                
                self.statusbar.showMessage("[%.3fs] Synced"%(time.time() - start_time))
                self.leftTreeWidget.clear()
                self.rightTreeWidget.clear()
                lpath, rpath = self.Sanity()
                self.Compare(lpath, rpath)
                message = QMessageBox.information(self,
                                                  "Success - Smart Synchroniser", "Succesfully finished synchronisation!")
                
#        except AssertionError, why:
#            self.updateStatus("[%.3fs] Synchronisation failed!"%(time.time() - start_time))
#            QMessageBox.critical(self, unicode("AssertionError - Smart Synchroniser"), unicode(why))
        except OSError, why:
            self.updateStatus("[%.3fs] Synchronisation failed!"%(time.time() - start_time))
            QMessageBox.critical(self, unicode("OSError - Smart Synchroniser"), unicode(why))            
#        except Exception:
#            self.updateStatus("[%.3fs] Synchronisation failed!"%(time.time() - start_time))
#            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
#            QMessageBox.critical(self, unicode("Oops! - Smart Synchroniser)"), 
#                                 unicode("Synchronisation could not be completed.\n\
#Please report this issue to the developer with the following information:\n\n\
#%s\n%s\n%s" %(exceptionType, exceptionValue, exceptionTraceback)))
#



    @pyqtSignature("")
    def on_profilesPushButton_pressed(self):
        #TODO:show profiles menu
        pass

    @pyqtSignature("")
    def on_helpPushButton_pressed(self):
        #TODO:show help menu
        pass

    @pyqtSignature("")
    def on_closePushButton_pressed(self):
        #TODO:save profile
        settings = QSettings()
        settings.setValue("MainWindow/Size", QVariant(self.size()))
        settings.setValue("MaingWindow/Position", QVariant(self.pos()))
        settings.setValue("MainWindow/State", QVariant(self.saveState()))

        if self.trash and os.path.isdir(self.trash):
            call(['rm', '-Rf', self.trash])
            
        print "Bye!"
    

        
if __name__ == "__main__":
    #TODO add CLI:
    #    --nogui
    #    --verbose
    
    leftdir, rightdir = None, None
    if len(sys.argv) > 2:
        leftdir, rightdir = sys.argv[-2:]
    app = QApplication(sys.argv)
    smartsync = Syncus(leftdir=leftdir, rightdir=rightdir, verbose=False)
    smartsync.show()
    app.exec_()

# End of file
