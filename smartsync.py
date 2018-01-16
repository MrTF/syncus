

#from PyQt4.QtCore import QThread,  QMutex,  QReadWriteLocker,  QReadLocker
from PyQt4.QtCore import *

class SmartSync(QThread):

    def __init__(self, lock, parent=None):        
        super(SmartSync,  self).__init__(parent)
        self.lock = lock 
        self.stopped = False
        self.mutex = QMutex()
        self.synced = False
        
    def initialize(self,  unidir, l2r,  r2l,  cliArgs, 
                   l2rJobQueue,  r2lJobQueue ):                       
        self.unidir = unidir
        self.l2r = l2r
        self.r2l = r2l
        self.cliArgs = cliArgs
        self.l2rJobQueue = l2rJobQueue
        self.r2lJobQueue = r2lJobQueue
        self.synced = False
        
    def run(self):
        self.sync()
        self.stop()
        self.emit(SIGNAL("finished(bool)"),  self.synced)
        
    def stop(self):
        with QMutexLocker(self.mutex):
            self.stopped = True
            
    def isStoppted(self):
        with QMutexLocker(self.mutex):
            return self.stopped
            

    def sync(self):
        '''This method is invoked when the "Synchronise" button is click.
        It will process the job queues prepared by self.Compare.
        '''
        
        print type(self.l2rJobQueue)
        print dir(self.l2rJobQueue)
        print self.l2rJobQueue
        print 
        print self.l2rJobQueue.__length_hint__()
        print self.l2rJobQueue.next()

        
        if not self.unidir or (self.unidir and self.l2rRadioButton.isChecked()):
            for source, destination in self.l2rJobQueue.iteritems():
                command = ['cp', source, destination] + self.cliArgs
                if not self.isStoppped():
                    if call(command) != 0:
                        raise Exception(unicode("E: Unknown synchronisation error occurred."))
                    else:
                        with QWriteLocker(self.lock):
                            del self.l2rJobQueue[source]
                
        
        if not self.unidir or (self.unidir and self.r2lRadioButton.isChecked()):
            for source, destination in self.r2lJobQueue.iteritems():
                command = ['cp', source, destination] + self.cliArgs
                if not self.isStoppped():
                    if call(command) != 0:
                        raise Exception(unicode("E: Unknown synchronisation error occurred."))
                    else:
                        with QWriteLocker(self.lock):
                            del self.r2lJobQueue[source]
                    
#        with QWriteLocker(self.lock):
#            self.l2rJobQueue = {}
#            self.r2lJobQueue = {}
        
        self.synced = True
        
