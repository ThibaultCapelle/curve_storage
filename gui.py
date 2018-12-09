# -*- coding: utf-8 -*-
"""
Created on Thu Dec  6 15:11:28 2018

@author: Thibault
"""

from PyQt5.QtWidgets import (QApplication,
QMessageBox, QGridLayout, QHBoxLayout, QLabel, QWidget, QVBoxLayout,
QLineEdit, QTableWidget, QSpinBox, QTableWidgetItem, QAbstractItemView,
QCheckBox, QTreeWidget, QTreeWidgetItem)
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
        self.tree_widget = TreeWidget()
        self.param_widget = ParamWidget(self.layout)
        self.layout_global.addWidget(self.param_widget)
        self.show_first_label = QLabel('show first')
        self.layout_show_first.addWidget(self.spinbox_widget)
        self.layout_left.addWidget(self.tree_widget)
        self.layout_show_first.addWidget(self.show_first_label)
        self.layout_right.addWidget(self.plot_widget)
        self.spinbox_changed.connect(self.tree_widget.compute)
        self.row_changed.connect(self.plot_widget.plot)
        self.row_changed.connect(self.param_widget.actualize)
        self.spinbox_widget.setValue(20)
        self.setLayout(self.layout_global)
        self.setGeometry(QRect(0, 0, 1000, 600))
        self.setMaximumHeight(600)
        self.show()
        self.move(0,0)
        
        
class ParamWidget(QTableWidget):
    
    def __init__(self, layout):
        super().__init__()
        self.layout=layout
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Param', 'Value'])
        self.verticalHeader().setVisible(False)
        self.setMaximumWidth(300)
    
    def actualize(self):
        item = self.window().tree_widget.active_item
        curve_id = int(item.data(0,0))
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

class TreeWidget(QTreeWidget):
    
    def __init__(self):
        super().__init__()
        self.setColumnCount(3)
        self.length = np.min([len(data.keys()), 20])
        self.setHeaderLabels(['Id', 'Name', 'Date'])
        for i in range(3):
            self.setColumnWidth(i,50)
        self.currentItemChanged.connect(self.current_item_changed)
        self.compute(first_use=True)
        
        
    def current_item_changed(self, item, previous_item):
        self.active_item = item
        self.window().row_changed.emit()

    def compute(self, first_use=False):
        self.clear()
        if first_use:
            new_size=20
        else:
            new_size = self.window().spinbox_widget.current_value
        if new_size!=self.length or first_use:
            data = DataBase().get_data()
            i=0
            keys = list(data.keys())
            N=len(keys)
            while(self.topLevelItemCount()<new_size):
                key = keys[N-i-1]
                value = data[key]
                curve = DataBase().get_curve(key)
                if str(curve.parent)==curve.id:
                    data.pop(key)
                    item=QTreeWidgetItem()
                    item.setData(0,0,key)
                    item.setData(2,0,time.strftime("%Y/%m/%d %H:%M:%S",time.gmtime(value)))
                    item.setData(1,0, curve.name) 
                    self.addTopLevelItem(item)
                    for child in curve.childs:
                        data = self.add_child(item, data, child)  
                i=i+1
            self.sortItems(2,QtCore.Qt.DescendingOrder)
            
        
    def add_child(self, item, data, child):
        child = DataBase().get_curve(child)
        t = data.pop(str(child.id))
        child_item=QTreeWidgetItem()
        child_item.setData(0,0,child.id)
        child_item.setData(2,0,time.strftime("%Y/%m/%d %H:%M:%S",time.gmtime(t)))
        child_item.setData(1,0, child.name)
        item.addChild(child_item)
        for grandchild in child.childs:
            data = self.add_child(child, data, grandchild)
        return data
        

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
        item = self.window().tree_widget.active_item
        curve_id = int(item.data(0,0))
        curve = DataBase().get_curve(curve_id)
        self.getPlotItem().clear()
        self.getPlotItem().plot(curve.x, curve.y)
        
        
        
        
data = DataBase().get_data()
app = QtCore.QCoreApplication.instance()
if app is None:
    app = QApplication(sys.argv)
window = WindowWidget()
app.exec_()


