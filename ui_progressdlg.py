#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'progressdlg-2.ui'
#
# Created: Mon Mar  9 14:57:05 2009
#      by: PyQt4 UI code generator 4.4.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_progressdlg(QtCore.QObject):
    def __init__(self,  parent=None):
        super(Ui_progressdlg,  self).__init__(parent)
        
    def setupUi(self, progressdlg):
        progressdlg.setObjectName("progressdlg")
        progressdlg.setWindowModality(QtCore.Qt.ApplicationModal)
        progressdlg.resize(400, 170)
        progressdlg.setMinimumSize(QtCore.QSize(400, 170))
        progressdlg.setMaximumSize(QtCore.QSize(600, 200))
        progressdlg.setModal(True)
        self.gridLayout = QtGui.QGridLayout(progressdlg)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.lr2Label = QtGui.QLabel(progressdlg)
        self.lr2Label.setObjectName("lr2Label")
        self.verticalLayout.addWidget(self.lr2Label)
        self.l2rProgressBar = QtGui.QProgressBar(progressdlg)
        self.l2rProgressBar.setProperty("value", QtCore.QVariant(0))
        self.l2rProgressBar.setObjectName("l2rProgressBar")
        self.verticalLayout.addWidget(self.l2rProgressBar)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.r2lLabel = QtGui.QLabel(progressdlg)
        self.r2lLabel.setObjectName("r2lLabel")
        self.verticalLayout.addWidget(self.r2lLabel)
        self.r2lProgressBar = QtGui.QProgressBar(progressdlg)
        self.r2lProgressBar.setProperty("value", QtCore.QVariant(0))
        self.r2lProgressBar.setInvertedAppearance(True)
        self.r2lProgressBar.setObjectName("r2lProgressBar")
        self.verticalLayout.addWidget(self.r2lProgressBar)
        spacerItem1 = QtGui.QSpacerItem(20, 28, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)
        self.buttonBox = QtGui.QDialogButtonBox(progressdlg)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Close|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)

        self.retranslateUi(progressdlg)
        #QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.Progress)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), progressdlg.reject)
        QtCore.QMetaObject.connectSlotsByName(progressdlg)
        
        


    def retranslateUi(self, progressdlg):
        progressdlg.setWindowTitle(QtGui.QApplication.translate("progressdlg", "Synchronisation process", None, QtGui.QApplication.UnicodeUTF8))
        self.lr2Label.setText(QtGui.QApplication.translate("progressdlg", "Synchronising from left to right...", None, QtGui.QApplication.UnicodeUTF8))
        self.r2lLabel.setText(QtGui.QApplication.translate("progressdlg", "Synchronising from right to left...", None, QtGui.QApplication.UnicodeUTF8))
        
    def Progress(self,  leftP=None,  rightP=None):
        if leftP:
            self.l2rProgressBar.setValue(lp)
        else:
            self.l2rProgressBar.setEnabled(False)
        if rightP:
            self.r2lProgressBar.setValue(lp)
        else:
            self.r2lProgressBar.setEnabled(False)
        
        
        
if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    progressdlg = QtGui.QDialog()
    ui = Ui_progressdlg()
    ui.setupUi(progressdlg)
    progressdlg.show()
    sys.exit(app.exec_())

