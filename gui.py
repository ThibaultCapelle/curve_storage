# -*- coding: utf-8 -*-
"""
Created on Thu Dec  6 15:11:28 2018

@author: Thibault
"""

from PyQt5.QtWidgets import (QApplication,
QMessageBox, QGridLayout, QHBoxLayout, QLabel, QWidget, QVBoxLayout,
QLineEdit, QTableWidget, QSpinBox, QTableWidgetItem, QAbstractItemView)
from PyQt5.QtCore import QRect
import PyQt5.QtCore as QtCore
import sys, time, os
from curve_storage.database import DataBase, Curve
import pyqtgraph as pg
import numpy as np


class WindowWidget(QWidget):
    
    spinbox_changed = QtCore.Signal()
    database_changed = QtCore.QFileSystemWatcher([DataBase().database_location])
    row_changed = QtCore.Signal()
    
    def __init__(self):
        super().__init__()
        self.layout_global = QHBoxLayout()
        self.layout_left = QVBoxLayout()
        self.layout_right = QVBoxLayout()
        self.plot_widget = PlotWidget()
        self.layout_show_first = QHBoxLayout()
        self.layout_global.addLayout(self.layout_left)
        self.layout_global.addLayout(self.layout_right)
        self.layout_left.addLayout(self.layout_show_first)
        self.spinbox_widget = SpinBoxWidget()
        self.table_widget = TableWidget(self.layout)
        self.param_widget = ParamWidget(self.layout)
        self.layout_global.addWidget(self.param_widget)
        self.show_first_label = QLabel('show first')
        self.layout_show_first.addWidget(self.spinbox_widget)
        self.layout_left.addWidget(self.table_widget)
        self.layout_show_first.addWidget(self.show_first_label)
        self.layout_right.addWidget(self.plot_widget)
        self.spinbox_changed.connect(self.table_widget.recompute_table)
        self.row_changed.connect(self.plot_widget.plot)
        self.row_changed.connect(self.param_widget.actualize)
        self.database_changed.fileChanged.connect(self.table_widget.recompute_table)
        self.spinbox_widget.setValue(20)
        self.setLayout(self.layout_global)
        self.setGeometry(QRect(0, 0, 1000, 600))
        self.setMaximumHeight(600)
        self.table_widget.recompute_table(first_use=True)
        self.show()
        self.move(0,0)
        
    
    def recompute_dimensions(self):
        self._width = 1000
        self._height = np.sum([self.table_widget.rowHeight(i) for i in range(self.table_widget.length)])
        self._height = self._height+self.table_widget.horizontalHeader().height()
        self._height = self._height+\
        self.table_widget.horizontalScrollBar().height()+\
        self.spinbox_widget.height()+30
        self._height= np.min([self._height, 800])
        self.setGeometry(QRect(self.geometry().x(),
                         self.geometry().y(),
                         self._width,
                         self._height))
        
class ParamWidget(QTableWidget):
    
    def __init__(self, layout):
        super().__init__()
        self.layout=layout
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Param', 'Value'])
        self.verticalHeader().setVisible(False)
        self.setMaximumWidth(300)
    
    def actualize(self):
        row = self.window().table_widget.active_row
        curve_id = int(self.window().table_widget.item(row, 0).text())
        curve = DataBase().get_curve(curve_id)
        self.clear()
        self.setHorizontalHeaderLabels(['Param', 'Value'])
        self.setRowCount(len(curve.params.keys()))
        for i,(k, v) in enumerate(curve.params.items()):
            key = QTableWidgetItem()
            key.setText(k)
            self.setItem(i,0,key)
            value = QTableWidgetItem()
            value.setText(str(v))
            self.setItem(i,1,value)
            
        
class TableWidget(QTableWidget):
    
    
    def __init__(self, layout):
        super().__init__()
        self.layout=layout
        self.setColumnCount(3)
        self.length = np.min([len(data.keys()), 20])
        self.setRowCount(self.length)
        for i in range(self.length):
            self.setRowHeight(i, 20)
        for i in range(3):
            self.setColumnWidth(i, 50)
        self.setHorizontalHeaderLabels(['Id', 'Name', 'Date'])
        self.verticalHeader().setVisible(False)
        self.cellPressed.connect(self.cell_clicked)
        self.currentCellChanged.connect(self.current_cell_changed)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.active_row=None
        self.setMaximumWidth(500)
        
        #self.setSortingEnabled(True)
        
        #self.setGeometry(QRect(9,8,100,100))
        #self.setSize(np.sum([self.columnWidth(i) for i in range(3)]),192)
    
    def cell_clicked(self, row, column):
        self.active_row=row
        
    def current_cell_changed(self, row, column, previous_row, previous_column):
        #if previous_row !=-1 and previous_column !=-1:
        self.active_row=row
        self.window().row_changed.emit()
            
    def recompute_table(self, first_use=False):
        if first_use:
            new_size=20
        else:
            new_size = self.window().spinbox_widget.current_value
        if new_size!=self.length or first_use:
            DataBase().equalize_with_data()
            data = DataBase().get_data()
            self.length = np.min([len(data.keys()), new_size])
            self.setRowCount(self.length)
            N = len(data.keys())
            for i, (k, v) in enumerate(data.items()):
                if np.abs(N-i-1)<self.length:
                    self.setItem(N-i-1, 0, QTableWidgetItem(k))
                    date = QTableWidgetItem()
                    date.setText(time.strftime("%Y/%m/%d %H:%M:%S",time.gmtime(v)))
                    self.setItem(N-i-1, 2, date)
                    name = QTableWidgetItem()
                    name.setText(DataBase().get_curve(k).name)
                    self.setItem(N-i-1,1, name)
                    #print('i={:}, k={:}, v={:}'.format(i, k, v))
            #self.sortItems(2, QtCore.Qt.DescendingOrder)
            self.window().recompute_dimensions()
        
        
class SpinBoxWidget(QSpinBox):
    
    def __init__(self):
        super().__init__()
        self.editingFinished.connect(self.editing_finished)
        self.current_value = self.value()
        self.setMaximumWidth(100)
        
        
    def editing_finished(self):
        self.current_value=self.value()
        self.window().spinbox_changed.emit()

class PlotWidget(pg.PlotWidget):
    
    def __init__(self):
        super().__init__()
        
    def plot(self):
        row = self.window().table_widget.active_row
        curve_id = int(self.window().table_widget.item(row, 0).text())
        curve = DataBase().get_curve(curve_id)
        self.getPlotItem().clear()
        self.getPlotItem().plot(curve.x, curve.y)
        
        
        
        
data = DataBase().get_data()
app = QtCore.QCoreApplication.instance()
if app is None:
    app = QApplication(sys.argv)
window = WindowWidget()
app.exec_()


