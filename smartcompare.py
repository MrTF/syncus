#!/usr/bin/env python
#
# Copyright 2009 Fatih Tumen
# fthtmn _eta_ googlemail.com
#
# This file is a part of Smart Synchroniser Project
# File and directory comparison module
# smartcompare.py 
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

__version__ = "$Revision: 4 $"


import os
import stat
from itertools import ifilter, ifilterfalse, imap, izip

__all__ = ["cmp","dircmp","cmpfiles"]

_cache = {}
BUFSIZE=8*1024

def cmp(f1, f2, shallow=True):
    """Compare two files.

    Arguments:

    f1 -- First file name

    f2 -- Second file name

    shallow -- Just check stat signature (do not read the files).
               defaults to 1.

    Return value:

    True if the files are the same, False otherwise.

    This function uses a cache for past comparisons and the results,
    with a cache invalidation mechanism relying on stale signatures.

    """

    s1 = _sig(os.stat(f1))
    s2 = _sig(os.stat(f2))
    if s1[0] != stat.S_IFREG or s2[0] != stat.S_IFREG:
        return 3
    if shallow:
        if s1 == s2:
            return 2
        else:
            return s1[2] < s2[2]
    
    #compare by content
    if s1[1] != s2[1]:
        return s1[2] < s2[2]

    result = _cache.get((f1, f2))
    if result and (s1, s2) == result[:2]:
        return result[2]
    outcome = _do_cmp(f1, f2)
    _cache[f1, f2] = s1, s2, outcome
    if outcome:
        return 2
    else:
        return s1[2] < s2[2] 

def _sig(st):
    return (stat.S_IFMT(st.st_mode),
            st.st_size,
            st.st_mtime)

def _do_cmp(f1, f2):
    bufsize = BUFSIZE
    fp1 = open(f1, 'rb')
    fp2 = open(f2, 'rb')
    while True:
        b1 = fp1.read(bufsize)
        b2 = fp2.read(bufsize)
        if b1 != b2:
            return False
        if not b1:
            return True

# Directory comparison class.
#

global Everything
Everything = {}

class dircmp:
    """A class that manages the comparison of 2 directories.

    dircmp(a,b,ignore=None,hide=None)
      A and B are directories.
      IGNORE is a list of names to ignore,
        defaults to ['RCS', 'CVS', 'tags'].
      HIDE is a list of names to hide,
        defaults to [os.curdir, os.pardir].

    High level usage:
      x = dircmp(dir1, dir2)
      x.report() -> prints a report on the differences between dir1 and dir2
       or
      x.report_partial_closure() -> prints report on differences between dir1
            and dir2, and reports on common immediate subdirectories.
      x.report_full_closure() -> like report_partial_closure,
            but fully recursive.

    Attributes:
     left_list, right_list: The files in dir1 and dir2,
        filtered by hide and ignore.
     common: a list of names in both dir1 and dir2.
     left_only, right_only: names only in dir1, dir2.
     common_dirs: subdirectories in both dir1 and dir2.
     common_files: files in both dir1 and dir2.
     common_funny: names in both dir1 and dir2 where the type differs between
        dir1 and dir2, or the name is not stat-able.
     same_files: list of identical files.
     left_only: list of filenames in dir1 which are more recently changed than those in dir2.
     right_only: list of filenames in dir2 which are more recently changed than those in dir1.
     funny_files: list of files which could not be compared.
     subdirs: a dictionary of dircmp objects, keyed by names in common_dirs.
     """
    

    def __init__(self, a, b, ignore=None, hide=None, shallow=True ):
        self.left = a
        self.right = b
        self.shallow = shallow
        if hide is None:
            self.hide = [os.curdir, os.pardir] 
        else:
            self.hide = hide
        
        self.ignore = ignore            

        
    def phase0(self):
        '''Compare everything except common subdirectories
        '''
        
        self.left_list = _filter(os.listdir(self.left),
                                 self.hide+self.ignore)
        self.right_list = _filter(os.listdir(self.right),
                                  self.hide+self.ignore)
        self.left_list.sort()
        self.right_list.sort()

    def phase1(self):
        '''Compute common names
        '''
        a = dict(izip(imap(os.path.normcase, self.left_list), self.left_list))
        b = dict(izip(imap(os.path.normcase, self.right_list), self.right_list))
        self.common = map(a.__getitem__, ifilter(b.has_key, a))
        self.left_only = map(a.__getitem__, ifilterfalse(b.has_key, a))
        self.right_only = map(b.__getitem__, ifilterfalse(a.has_key, b))

    def phase2(self):
        '''Distinguish files, directories, funnies
        '''
    
        self.common_dirs = []
        self.common_files = []
        self.common_funny = []

        for x in self.common:
            a_path = os.path.join(self.left, x)
            b_path = os.path.join(self.right, x)

            ok = 1
            try:
                a_stat = os.stat(a_path)
            except os.error, why:
                # print 'Can\'t stat', a_path, ':', why[1]
                ok = 0
            try:
                b_stat = os.stat(b_path)
            except os.error, why:
                # print 'Can\'t stat', b_path, ':', why[1]
                ok = 0

            if ok:
                a_type = stat.S_IFMT(a_stat.st_mode)
                b_type = stat.S_IFMT(b_stat.st_mode)
                if a_type != b_type:
                    self.common_funny.append(x)
                elif stat.S_ISDIR(a_type):
                    self.common_dirs.append(x)
                elif stat.S_ISREG(a_type):
                    self.common_files.append(x)
                else:
                    self.common_funny.append(x)
            else:
                self.common_funny.append(x)

    def phase3(self):
        '''Find out differences between common files
        '''
        xx = cmpfiles(self.left, self.right, self.common_files, self.shallow)
        self.same_files, self.left_recent, self.right_recent, self.funny_files = xx

    def phase4(self):
        '''Find out differences between common sub-directories
        A new dircmp object is created for each common sub-directory,
        these are stored in a dictionary indexed by filename.
        The hide and ignore properties are inherited from the parent
        '''
        self.subdirs = {}
        for x in self.common_dirs:
            a_x = os.path.join(self.left, x)
            b_x = os.path.join(self.right, x)
            self.subdirs[x]  = dircmp(a_x, b_x, self.ignore, self.hide)

    def phase4_closure(self):
        '''Recursively call phase4() on sub-directories
        '''
        
        self.phase4()
        for sd in self.subdirs.itervalues():
            sd.phase4_closure()

    def report(self):
        '''Print a report on the differences between a and b
        '''

#        if self.left: print "LEFT:\t", self.left
#        if self.right: print "RIGHT:\t", self.right
#        if self.left_only: print 'LONLY', self.left_only
#        if self.right_only: print 'RONLY', self.right_only
#        if self.left_recent: print 'LRECENT', self.left_recent
#        if self.right_recent: print 'RRECENT', self.right_recent
#        if self.common_dirs: print 'COMMONDIR', self.common_dirs
#        if self.common_funny: print 'cFUNNY', self.common_funny
#        if self.funny_files: print 'FUNNY', self.funny_files
        
        if self.left_only:
            self.left_only.sort()
            for each in self.left_only:
                Everything[os.path.join(self.left, each)] = 'left_only'

        if self.right_only:
            self.right_only.sort()
            for each in self.right_only:
                Everything[os.path.join(self.right, each)] = 'right_only'

        if self.same_files:
            self.same_files.sort()
            for each in self.same_files:
                Everything[os.path.join(self.left, each)] = 'same_files'
                Everything[os.path.join(self.right, each)] = 'same_files'

        if self.left_recent:
            self.left_recent.sort()
            for each in self.left_recent:
                Everything[os.path.join(self.left, each)] = 'left_recent'

        if self.right_recent:
            self.right_recent.sort()
            for each in self.right_recent:
                Everything[os.path.join(self.right, each)] = 'right_recent'

        if self.funny_files:
            self.funny_files.sort()
            for each in self.funny_files:
                Everything[os.path.join(self.left, each)] = 'funny_files'
                Everything[os.path.join(self.right, each)] = 'funny_files'

        if self.common_dirs:
            self.common_dirs.sort()
            for each in self.common_dirs:
                Everything[os.path.join(self.left, each)] = 'common_dirs'
                Everything[os.path.join(self.right, each)] = 'common_dirs'

        if self.common_funny:
            self.common_funny.sort()
            for each in self.common_funny:
                Everything[os.path.join(self.left, each)] = 'common_funny'
                Everything[os.path.join(self.right, each)] = 'common_funny'

    def report_partial_closure(self): 
        '''Report on self and on subdirs
        '''
        
        self.report()
        for sd in self.subdirs.itervalues():
            print
            sd.report()

    def report_full_closure(self):
        '''Report on self and subdirs recursively
        '''
        
        self.report()
        for sd in self.subdirs.itervalues():
            sd.report_full_closure()
            
    def everything(self):
        """Return Everything dictionary which is populated once report*()
        methods is called
        """
        return Everything

    methodmap = dict(subdirs=phase4, left_recent=phase3, right_recent=phase3,
                     same_files=phase3, diff_files=phase3, funny_files=phase3,
                     common_dirs = phase2, common_files=phase2, common_funny=phase2,
                     common=phase1, left_only=phase1, right_only=phase1,
                     left_list=phase0, right_list=phase0, Everything=everything)

    def __getattr__(self, attr):
        if attr not in self.methodmap:
            raise AttributeError, attr
        self.methodmap[attr](self)
        return getattr(self, attr)

def cmpfiles(a, b, common, shallow=True):
    """Compare common files in two directories.

    a, b -- directory names
    common -- list of file names found in both directories
    shallow -- if true, do comparison based solely on stat() information

    Returns a tuple of four lists:
      files that compare equal
      files in a that are more recently changed (than those in b)
      files in b that are more recently changed (than those in a)
      filenames that aren't regular files.
    """
    
    res = ([], [], [], [])
    for x in common:
        ax = os.path.join(a, x)
        bx = os.path.join(b, x)
        res[_cmp(ax, bx, shallow)].append(x)

    return res


def _cmp(a, b, sh, abs=abs, cmp=cmp):
    ''' Compare two files.
    Return:
           0 for left recent
           1 for right recent
           2 for equal
           3 for funny cases (can't stat, etc.)
    '''
    
    try:
        return abs(cmp(a, b, sh))
    except os.error:
        return 3



def _filter(flist, skip):
    '''Return a copy with items that occur in skip removed.
    '''
    return list(ifilterfalse(skip.__contains__, flist))


# End of file
