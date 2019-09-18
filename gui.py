# -*- coding: utf-8 -*-
"""
Created on Thu Dec  6 15:11:28 2018

@author: Thibault
"""

from PyQt5.QtWidgets import (QApplication,
QMessageBox, QGridLayout, QHBoxLayout, QLabel, QWidget, QVBoxLayout,
QLineEdit, QTableWidget, QSpinBox, QTableWidgetItem, QAbstractItemView,
QCheckBox, QTreeWidget, QTreeWidgetItem, QMenu)
from PyQt5.QtCore import QRect, QPoint
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import sys, time, os
from curve_storage.database import Curve, SQLDatabase
import pyqtgraph as pg
import numpy as np

N_ROW_DEFAULT=20

class WindowWidget(QWidget):
    
    spinbox_changed = QtCore.Signal()
    database_changed = QtCore.QFileSystemWatcher([SQLDatabase.DATABASE_LOCATION])
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
        self.database_changed.directoryChanged.connect(self.tree_widget.compute)
        self.spinbox_widget.setValue(20)
        self.setLayout(self.layout_global)
        self.setGeometry(QRect(0, 0, 1000, 600))
        self.setMaximumHeight(600)
        self.show()
        self.move(0,0)
    
    def moveEvent(self,event):
        self.tree_widget.move()
        
    def mousePressEvent(self, event):
        self.tree_widget.move()
    
    def resizeEvent(self, event):
        self.tree_widget.move()
        
class QTreeContextMenu(QMenu):
    
    def __init__(self, item):
        super().__init__()
        self.item=item
        self.tree_widget=self.item.treeWidget()
        #self.move()
        self.item_position=self.tree_widget.visualItemRect(self.item)
        self.window_position=self.tree_widget.window().geometry()
        self.tree_position=self.tree_widget.geometry()
        #self.header_position=self.item.treeWidget().header().geometry()
        self.setGeometry(self.item_position.translated(self.window_position.topLeft()).translated(self.tree_position.topLeft()))
        #self.setGeometry(self.geometry().translated(self.layout_left_position.topLeft()))
        self.delete_action=self.addAction("delete")
        self.delete_action.triggered.connect(self.delete)
        self.height=self.geometry().height()
        self.setVisible(True)
        self.show()
    
    def move(self):
        self.item_position=self.tree_widget.visualItemRect(self.item).setHeight(self.height)
        self.tree_position=self.tree_widget.geometry()
        self.window_position=self.tree_widget.window().geometry()
        self.layout_left_position=self.tree_widget.window().layout_left.geometry()
        #self.header_position=self.item.treeWidget().header().geometry()
        #self.setGeometry(self.item_position.translated(self.window_position.topLeft()).translated(self.tree_position.topLeft()))
        #self.setGeometry(self.geometry().translated(self.layout_left_geometry().topLeft()))
        self.setGeometry(self.item_position.translated(self.window_position.topLeft()).translated(self.tree_position.topLeft()))
        #self.setGeometry(self.geometry().translated(self.layout_left_position.topLeft()))
        self.show()
        
    def delete(self):
        next_item=None
        self.selected_items=self.tree_widget.selectedItems()
        selection=self.selected_items
        while((len(selection)>0) and ((next_item is None) or (next_item in self.selected_items))):
            item=selection.pop()
            next_item=self.tree_widget.itemBelow(item)
            if(next_item is None):
                next_item=self.tree_widget.itemAbove(item)
        for item in self.selected_items:
            curve_id=item.data(0,0)
            SQLDatabase().delete_entry(curve_id)
        self.setVisible(False)
        if next_item is not None:
            self.tree_widget.setCurrentItem(next_item)
            next_item.setSelected(1)
        
       
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
        curve = SQLDatabase().get_curve(curve_id)
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
        self.length = np.min([SQLDatabase().get_n_keys(), N_ROW_DEFAULT])
        self.setHeaderLabels(['Id', 'Name', 'Date'])
        for i in range(3):
            self.setColumnWidth(i,50)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.currentItemChanged.connect(self.current_item_changed)
        self.compute(first_use=True)
        self.itemActivated.connect(self.compute)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.contextMenu=None
        self.customContextMenuRequested.connect(self.RightClickMenu)
    
    def move(self):
        if self.contextMenu is not None:
            self.contextMenu.move()
            
    def RightClickMenu(self, point):
        item=self.itemAt(point)
        self.contextMenu=QTreeContextMenu(item)
        
    def current_item_changed(self, item, previous_item):
        self.active_item = item
        self.window().row_changed.emit()

    def compute(self, first_use=False):
        if first_use:
            new_size=N_ROW_DEFAULT
        else:
            new_size = self.window().spinbox_widget.current_value
        if new_size!=self.length or first_use:
            self.clear()
            database=SQLDatabase()
            keys = database.get_all_ids()
            N=len(keys)
            new_size=np.min([N,new_size])
            i=0
            #keys = list(data.keys())
            
            while(len(keys)>0 and self.topLevelItemCount()<new_size and i<N):
                key = keys[-1]
                if key in keys:
                    curve_data = database.get_curve_metadata(key)
                    name, date, childs, parent, params = curve_data
                    #curve = DataBase().get_curve(key, retrieve_data=False)
                    if parent==key:
                        keys.remove(key)
                        item=QTreeWidgetItem()
                        item.setData(0,0,key)
                        item.setData(2,0,time.strftime("%Y/%m/%d %H:%M:%S",time.gmtime(date)))
                        item.setData(1,0, name) 
                        self.addTopLevelItem(item)
                        for child in childs:
                            keys = self.add_child(item, keys, child)  
                i=i+1
            self.sortItems(2,QtCore.Qt.DescendingOrder)
            
        
    def add_child(self, item, keys, child):
        #child = DataBase().get_curve(child)
        keys.remove(child)
        name, date, childs, parent, params = SQLDatabase().get_curve_metadata(child)
        child_item=QTreeWidgetItem()
        child_item.setData(0,0,str(child))
        child_item.setData(2,0,time.strftime("%Y/%m/%d %H:%M:%S",time.gmtime(date)))
        child_item.setData(1,0, name)
        item.addChild(child_item)
        for grandchild in childs:
            keys = self.add_child(child_item, keys, grandchild)
        return keys
        

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
        curve = SQLDatabase().get_curve(curve_id)
        self.getPlotItem().clear()
        self.getPlotItem().plot(curve.x, curve.y)
        
        
        
        
#data = DataBase().get_data()
app = QtCore.QCoreApplication.instance()
if app is None:
    app = QApplication(sys.argv)
window = WindowWidget()
curve_1=Curve([0,1,2,3])
curve_2=Curve([0,1,2,3],[10,2,3,5], bonjour=[1,2,3])

#app.exec_()



