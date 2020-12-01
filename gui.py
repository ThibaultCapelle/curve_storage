# -*- coding: utf-8 -*-
"""
Created on Thu Dec  6 15:11:28 2018

@author: Thibault
"""

from PyQt5.QtWidgets import (QApplication,
QMessageBox, QGridLayout, QHBoxLayout, QLabel, QWidget, QVBoxLayout,
QLineEdit, QTableWidget, QSpinBox, QTableWidgetItem, QAbstractItemView,
QCheckBox, QTreeWidget, QTreeWidgetItem, QMenu, QPushButton, QComboBox,
QInputDialog)
from PyQt5.QtCore import QRect, QPoint
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import sys, time, os, subprocess
from curve_storage.database import Curve, SQLDatabase, transaction
import pyqtgraph as pg
import numpy as np
import json
import matplotlib.pylab as plt

N_ROW_DEFAULT=20

class WindowWidget(QWidget):
    
    spinbox_changed = QtCore.Signal()
    '''database_changed = QtCore.QFileSystemWatcher([os.path.join(SQLDatabase.DATABASE_LOCATION,
                                                               SQLDatabase.DATABASE_NAME)])'''
    row_changed = QtCore.Signal()
    
    
    def __init__(self):
        super().__init__()
        self.layout_global = QHBoxLayout()
        self.layout_left = QVBoxLayout()
        self.layout_center = QVBoxLayout()
        self.layout_right = QVBoxLayout()
        self.layout_top = QHBoxLayout()
        self.layout_bottom = QHBoxLayout()
        self.plot_widget = PlotWidget()
        
        self.layout_show_first = QHBoxLayout()
        self.layout_global.addLayout(self.layout_left)
        self.layout_global.addLayout(self.layout_center)
        self.layout_global.addLayout(self.layout_right)
        self.layout_left.addLayout(self.layout_show_first)
        self.spinbox_widget = SpinBoxWidget()
        self.show_specific_project = QCheckBox('Show specific project')
        self.project = Project('', self)
        self.tree_widget = TreeWidget(self.show_specific_project, self.project)
        self.plot_options = plotOptions(self.tree_widget)
        self.param_widget = ParamWidget(self.layout)
        self.layout_right.addWidget(self.param_widget)
        self.show_first_label = QLabel('show first')
        
        
        self.compute_button = QPushButton('update')
        self.layout_show_first.addWidget(self.show_first_label)
        self.layout_show_first.addWidget(self.spinbox_widget)
        self.layout_left.addWidget(self.tree_widget)
        self.layout_show_first.addWidget(self.show_specific_project)
        self.layout_show_first.addWidget(self.project)
        self.layout_show_first.addWidget(self.compute_button)
        self.layout_center.addLayout(self.layout_top)
        self.layout_top.addWidget(self.plot_options)
        self.layout_center.addWidget(self.plot_widget)
        self.directory_button = DirectoryButton(self.tree_widget)
        self.directory_button.clicked.connect(self.directory_button.action)
        self.layout_center.addLayout(self.layout_bottom)
        self.layout_bottom.addWidget(self.directory_button)
        self.plot_figure_button = PlotFigureButton(self.tree_widget,
                                                   self.plot_widget)
        self.plot_figure_button.clicked.connect(self.plot_figure_button.action)
        self.layout_bottom.addWidget(self.plot_figure_button)
        
        self.spinbox_changed.connect(self.tree_widget.compute)
        self.compute_button.clicked.connect(self.tree_widget.compute)
        self.row_changed.connect(self.plot_widget.plot)
        self.row_changed.connect(self.param_widget.actualize)
        self.row_changed.connect(self.directory_button.update)
        self.changing_tree=False
        #self.database_changed.fileChanged.connect(self.database_changed_slot)
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
    '''
    def database_changed_slot(self, path):
        print('database changed, changing_tree:{:}, path:{:}'.format(self.changing_tree, path))
        if not self.changing_tree:
            self.changing_tree=True
            self.tree_widget.compute()'''

class Project(QLineEdit):
    
    def __init__(self, text, window):
        super().__init__(text, parent=window)
        self.parent=window
        self.hide()
        self.parent.show_specific_project.stateChanged.connect(self.set_visible)
        
    
    def set_visible(self, state):
        if isinstance(state, bool):
            pass
        elif state==QtCore.Qt.Checked:
            self.show()
        elif state==QtCore.Qt.Unchecked:
            self.hide()
            self.parent.tree_widget.compute()
        else:
            pass
        
    def text_changed_slot(self, text):
        if not self.isHidden():
            self.parent.tree_widget.compute()
        
class plotOptions(QComboBox):
    
    def __init__(self, treewidget):
        super().__init__()
        self.treewidget=treewidget
        self.addItems(['Real', 'Imaginary', 'dB', 'Smith', 'Abs'])
        self.currentTextChanged.connect(self.update)
    
    def update(self, new_text):
        self.window().plot_widget.plot()


class DirectoryButton(QPushButton):

    def __init(self, treewidget):
        super().__init__()
        self.treewidget=treewidget
        self.current_id=None

    def update(self):
        if self.window().tree_widget.active_item is not None:
            self.current_id=self.window().tree_widget.active_item.data(0,0)
            db=SQLDatabase()
            cid, name, date=db.get_name_and_time(self.current_id)
            if not os.path.exists(db.get_folder_from_date(date)):
                self.setText('Create directory')
            else:
                self.setText('Go to directory')
    
    def startfile(self,filename):
        try:
            os.startfile(filename)
        except:
            subprocess.Popen(['xdg-open', filename])
    
    def action(self):
        db=SQLDatabase()
        cid, name, date=db.get_name_and_time(self.current_id)
        self.setText('Go to directory')
        directory=db.get_folder_from_date(date)
        if not str(self.current_id) in os.listdir(directory):
            os.mkdir(os.path.join(directory,str(self.current_id)))
        else:
            self.startfile(os.path.join(directory,str(self.current_id)))

class PlotFigureButton(QPushButton):
    
    def __init__(self, treewidget, plotwidget):
        super().__init__()
        self.treewidget=treewidget
        self.plotwidget=plotwidget
        self.setText('Plot Figure')
    
    def action(self):
        items=self.plotwidget.getPlotItem()
        current_id=self.treewidget.active_item.data(0,0)
        curve=Curve(current_id)
        for i, item in enumerate(items.items):
            rect=item.viewRect()
            xmin, ymin, xmax, ymax = (rect.left(), rect.bottom(), 
                                      rect.right(), rect.top())
            x, y = item.getData()
            plt.figure()
            plt.title('id : {:}'.format(current_id))
            state=self.window().plot_options.currentText()
            if state=='dB':
                plt.plot(np.real(x), 20*np.log10(np.abs(y)), '.')
            elif state=='Real':
                plt.plot(np.real(x), np.real(y), '.')
            elif state=='Imaginary':
                plt.plot(np.real(x), np.imag(y), '.')
            elif state=='Smith':
                plt.plot(np.real(y), np.imag(y), '.')
            elif state=='Abs':
                plt.plot(np.real(x), np.abs(y), '.')
            plt.xlim([xmin, xmax])
            plt.ylim([ymin, ymax])
            plt.savefig(os.path.join(curve.get_or_create_dir(), 'display.png'), dpi=100)
            
        
        
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
        self.setGeometry(self.item_position.
                         translated(self.window_position.topLeft())
                         .translated(self.tree_position.topLeft()))
        #self.setGeometry(self.geometry().translated(self.layout_left_position.topLeft()))
        self.delete_action=self.addAction("delete")
        self.delete_action.triggered.connect(self.delete)
        self.move_action=self.addAction("move")
        self.move_action.triggered.connect(self.move_curve)
        self.height=self.geometry().height()
        self.setVisible(True)
        self.show()
    
    def move_curve(self):
        self.selected_items=self.tree_widget.selectedItems()
        dialog = QInputDialog(self)
        parent_id, ok=dialog.getInt(self, 'move',
                                     'what is the desired parent ?')
        if ok:
            db=SQLDatabase()
            for item in self.selected_items:
                curve_id=int(item.data(0,0))
                db.move(curve_id, int(parent_id))
            self.tree_widget.compute()
        
    def delete(self):
        self.selected_items=self.tree_widget.selectedItems()
        selection=self.selected_items
        for item in selection:
            curve_id=item.data(0,0)
            SQLDatabase().delete_entry(curve_id)
        self.tree_widget.compute()

class QParamsContextMenu(QMenu):
    
    def __init__(self, point, window):
        super().__init__()
        self.window=window
        self.add_param_action=self.addAction("Add param")
        self.setVisible(True)
        self.show()
        self.window_position=self.window.geometry()
        #self.header_position=self.item.treeWidget().header().geometry()
        self.setFixedSize(100, 25)
        self.setGeometry(self.window_position.
                         translated(point)
                         .translated(self.window.param_widget.geometry().topLeft()))
       
class ParamWidget(QTableWidget):
    
    def __init__(self, layout):
        super().__init__()
        self.layout=layout
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Param', 'Value'])
        self.verticalHeader().setVisible(False)
        self.setMaximumWidth(300)
        #self.itemChanged.connect(self.item_changed)
        self.clicked_item=None
        self.previous_content=None
        #self.itemClicked.connect(self.item_clicked)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.contextMenu=None
        self.customContextMenuRequested.connect(self.RightClickMenu)
    
    def RightClickMenu(self, point):
        self.contextMenu=QParamsContextMenu(point, self.window())
    
    def actualize(self):
        item = self.window().tree_widget.active_item
        if item is not None:
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
    
    def mousePressEvent(self, event):
        if event.button()==QtCore.Qt.RightButton:
            tree = self.window().tree_widget
            if hasattr(tree, "active_item") and tree.active_item is not None:
                current_id=self.window().tree_widget.active_item.data(0,0)
                if current_id is not None:
                    pass
    
    def contextMenuEvent(self, event):
        current_id=self.window().tree_widget.active_item.data(0,0)
        if current_id is not None:
            self.menu = QMenu(self)
            addParamAction = self.menu.addAction("add new parameter")
            action = self.menu.exec_(self.mapToGlobal(event.pos()))
            if action == addParamAction:
                self.new_param_menu()
                self.menu.close()
                
    def new_param_menu(self):
        self.new_param_window=QWidget(self.window())
        self.new_param_layout=QHBoxLayout(self.new_param_window)
        self.name_layout=QVBoxLayout(self.new_param_window)
        self.name_text=QLabel('Name')
        self.name_text.setStyleSheet("QLabel { background-color : white; color : black; }")
        self.name_layout.addWidget(self.name_text)
        self.name_box=QLineEdit(self.new_param_window)
        self.name_layout.addWidget(self.name_box)
        self.new_param_layout.addLayout(self.name_layout)
        self.new_param_window.setLayout(self.new_param_layout)
        self.new_param_window.setGeometry(QRect(500, 250, 300, 100))
        self.param_layout=QVBoxLayout(self.new_param_window)
        self.param_text=QLabel('param')
        self.param_text.setStyleSheet("QLabel { background-color : white; color : black; }")
        self.param_layout.addWidget(self.param_text)
        self.param_box=QLineEdit(self.new_param_window)
        self.param_layout.addWidget(self.param_box)
        self.new_param_layout.addLayout(self.param_layout)
        self.button=QPushButton()
        self.button.setText('add new parameter')
        self.button.clicked.connect(self.get_new_param)
        self.new_param_layout.addWidget(self.button)
        self.new_param_window.show()
    
    def get_new_param(self):
        name, param = self.name_box.text(), self.param_box.text()
        current_id=self.window().tree_widget.active_item.data(0,0)
        curve=SQLDatabase().get_curve(current_id)
        curve.params[name]=param
        curve.save()
        self.new_param_window.close()
        

class TreeWidget(QTreeWidget):
    
    def __init__(self, show_specific_project, project):
        super().__init__()
        self.show_specific_project=show_specific_project
        self.project=project
        self.active_ID=None
        self.setColumnCount(3)
        self.length = np.min([SQLDatabase().get_n_keys(), N_ROW_DEFAULT])
        self.setHeaderLabels(['Id', 'Name', 'Date'])
        for i in range(3):
            self.setColumnWidth(i,50)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.currentItemChanged.connect(self.current_item_changed)
        self.compute(first_use=True)
        #self.itemActivated.connect(self.activation)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.contextMenu=None
        self.customContextMenuRequested.connect(self.RightClickMenu)
    
    def activation(self):
        print('item activated !')
        
    def move(self):
        if self.contextMenu is not None:
            self.contextMenu.move()
            
    def RightClickMenu(self, point):
        item=self.itemAt(point)
        if item is not None:
            self.contextMenu=QTreeContextMenu(item)
        
    def current_item_changed(self, item, previous_item):
        self.active_item = item
        if item is not None:
            self.active_ID = int(item.data(0,0))
        else:
            self.active_ID=None
        self.window().row_changed.emit()
    
    def compute(self, first_use=False):
        if first_use:
            new_size=N_ROW_DEFAULT
        else:
            new_size = self.window().spinbox_widget.current_value
        if self.show_specific_project.isChecked():
            project=self.project.text()
        else:
            project=None
        self.clear()
        database=SQLDatabase()
        keys = database.get_all_hierarchy(project=project)
        if project is not None:
            keys_copy=database.get_all_hierarchy(project=None)
        else:
            keys_copy=keys.copy()  
        keys.sort()
        keys_copy.sort()
        N=len(keys)
        new_size=np.min([N,new_size])
        i=0
        to_remove=[]
        while(len(keys)>0 and self.topLevelItemCount()<new_size and i<N):
            key, childs, parent = keys.pop()
            if parent==key and key not in to_remove:
                curve_id, name, date=database.get_name_and_time(key)
                item=QTreeWidgetItem()
                item.setData(0,0,key)
                item.setData(2,0,time.strftime("%Y/%m/%d %H:%M:%S",time.gmtime(float(date)+7200)))
                item.setData(1,0, name) 
                if key==self.active_ID:
                    self.setCurrentItem(item)
                self.addTopLevelItem(item)
                
                if childs not in ['[]', '{}']:
                    childs=json.loads(childs)
                    params_childs=database.get_name_and_time(childs)
                    for child in childs:
                        to_remove+= self.add_child(item, child, keys_copy, params_childs, database)
                
            i=i+1
        self.sortItems(2,QtCore.Qt.DescendingOrder)
        self.window().changing_tree=False
        
        
    def add_child(self, item, child, keys, params_childs, database):
        res=[child]
        params=None
        for val in params_childs:
            if(int(val[0])==child):
                params=val
        
        #params=SQLDatabase().get_name_and_time(child)
        if params is not None:
            for key in keys:
                if key[0]==child:
                    if key[1] not in ['[]', '{}']:
                        grandchilds=json.loads(key[1])
                    else:
                        grandchilds=[]
                    break      
            
            curve_id, name, date=params
            child_item=QTreeWidgetItem()
            child_item.setData(0,0,str(child))
            child_item.setData(2,0,time.strftime("%Y/%m/%d %H:%M:%S",time.gmtime(date+7200)))
            child_item.setData(1,0, name)
            
            if int(str(child))==self.active_ID:
                self.setCurrentItem(child_item)
            item.addChild(child_item)
            if len(grandchilds)>0:
                params_grandchilds=database.get_name_and_time(grandchilds)
            for grandchild in grandchilds:
                res+= self.add_child(child_item, grandchild, keys, 
                                     params_grandchilds, database)
        return res
        

class SpinBoxWidget(QSpinBox):
    
    def __init__(self):
        super().__init__()
        self.editingFinished.connect(self.editing_finished)
        self.current_value = self.value()
        self.setMaximumWidth(100)
        self.setMaximum(10000)
        
        
    def editing_finished(self):
        self.current_value=self.value()
        self.window().spinbox_changed.emit()

class PlotWidget(pg.PlotWidget):
    
    def __init__(self):
        super().__init__()
        
    def plot(self):
        item = self.window().tree_widget.active_item
        if item is not None:
            self.getPlotItem().enableAutoRange(enable=True)
            curve_id = int(item.data(0,0))
            curve = SQLDatabase().get_curve(curve_id)
            x, y_r, y_i, y_abs=(np.real(curve.x), np.real(curve.y),
                                np.imag(curve.y), np.abs(curve.y))
            self.getPlotItem().clear()
            
            state=self.window().plot_options.currentText()
            if state=='dB':
                self.getPlotItem().plot(x, 20*np.log10(y_abs))
            elif state=='Real':
                self.getPlotItem().plot(x, y_r)
            elif state=='Imaginary':
                self.getPlotItem().plot(x, y_i)
            elif state=='Smith':
                self.getPlotItem().plot(y_r, y_i)
            elif state=='Abs':
                self.getPlotItem().plot(x, y_abs)
            self.getPlotItem().enableAutoRange(enable=False)
            
        
        
#data = DataBase().get_data()
app = QtCore.QCoreApplication.instance()
if app is None:
    app = QApplication(sys.argv)
window = WindowWidget()
#curve_1=Curve([0,1,2,3])
#curve_2=Curve([0,1,2,3],[10,2,3,5], bonjour=[1,2,3])

sys.exit(app.exec_())


