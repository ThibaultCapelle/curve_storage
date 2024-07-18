# -*- coding: utf-8 -*-
"""
Created on Thu Dec  6 15:11:28 2018

@author: Thibault
"""

from PyQt5.QtWidgets import (QApplication,
QGridLayout, QHBoxLayout, QLabel, QWidget, QVBoxLayout,
QLineEdit, QTextEdit, QTableWidget, QSpinBox, QTableWidgetItem, 
QAbstractItemView, QCheckBox, QTreeWidget, QTreeWidgetItem, QMenu,
QPushButton, QComboBox, QInputDialog, QGroupBox, QToolButton,
QCalendarWidget, QRadioButton, QColorDialog, QFrame)
from PyQt5.QtCore import QRect, QPoint, QSize
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import sys, time, os, subprocess
from curve_storage.database import Curve, SQLDatabase, transaction, Filter
from curve_storage.fit import Fit
import pyqtgraph as pg
import numpy as np
import json
import matplotlib.pylab as plt
from psycopg2 import sql
from datetime import datetime as datetime
import h5py
import inspect

N_ROW_DEFAULT=20

class WindowWidget(QWidget):
    
    spinbox_changed = QtCore.pyqtSignal()
    pageno_changed = QtCore.pyqtSignal()
    row_changed = QtCore.pyqtSignal()
    
    
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Curve Database GUI')
        self.layout_global = QHBoxLayout()
        self.layout_left = QVBoxLayout()
        self.layout_center = QVBoxLayout()
        self.layout_right = QVBoxLayout()
        self.layout_top = QHBoxLayout()
        self.layout_bottom = QHBoxLayout()
        self.plot_widget = PlotWidget()
        #self.add_filters = QCheckBox('add_filters')
        self.show_filters = QCheckBox('Show filters')
        #self.show_filters.hide()
        self.filter_widget = MasterFilterWidget(self)
        self.show_filters.setChecked(True)
        self.layout_show_first = QGridLayout()
        self.layout_page_number = QHBoxLayout()
        self.layout_global.addWidget(self.filter_widget)
        self.layout_global.addLayout(self.layout_left)
        self.layout_global.addLayout(self.layout_center)
        self.layout_global.addLayout(self.layout_right)
        self.layout_left.addLayout(self.layout_show_first)
        self.layout_left.addLayout(self.layout_page_number)
        self.spinbox_widget = SpinBoxWidget()
        self.spinbox_widget.setValue(N_ROW_DEFAULT)
        self.page_number_spinbox = PageNumberWidget()
        
        
        self.param_widget = ParamWidget(self.layout)
        self.layout_right.addWidget(self.param_widget)
        self.show_first_label = QLabel('show first')
        self.page_number_label = QLabel('page number')
        self.layout_page_number.addWidget(self.page_number_label)
        self.layout_page_number.addWidget(self.page_number_spinbox)
        
        self.compute_button = QPushButton('update')
        self.layout_show_first.addWidget(QLabel('current project'), 0, 0,
                                         1, 2)
        self.current_project_widget=QLineEdit(SQLDatabase.get_project())
        self.current_project_widget.editingFinished.connect(self.update_project)
        self.layout_show_first.addWidget(self.current_project_widget, 0, 2,
                                         1, 3)
        self.layout_show_first.addWidget(self.show_first_label, 1, 0)
        self.layout_show_first.addWidget(self.spinbox_widget, 1, 1)
        
        self.layout_show_first.addWidget(self.show_filters, 1, 2)
        self.layout_show_first.addWidget(self.compute_button, 1, 3)
        self.layout_center.addLayout(self.layout_top)
        
        self.layout_center.addWidget(self.plot_widget)
        
        self.tree_widget = TreeWidget(self)
        self.layout_left.addWidget(self.tree_widget)
        self.plot_options = plotOptions(self.tree_widget)
        self.layout_top.addWidget(self.plot_options)
        self.directory_button = DirectoryButton(self.tree_widget)
        self.comment=Comment(self.tree_widget)
        self.layout_center.addWidget(self.comment)
        self.layout_center.addLayout(self.layout_bottom)
        self.layout_bottom.addWidget(self.directory_button)
        self.plot_figure_button = PlotFigureButton(self.tree_widget,
                                                   self.plot_widget)
        self.plot_figure_options_button = PlotFigureOptionButton(self)
        self.fit_functions=FitFunctions(self.tree_widget)
        self.fit_button = FitButton(self.tree_widget,
                                    self.plot_widget)
        self.save_fit_button = SaveFitButton(self.tree_widget,
                                    self.plot_widget)
        self.layout_bottom.addWidget(self.plot_figure_button)
        self.layout_bottom.addWidget(self.plot_figure_options_button)
        self.layout_bottom.addWidget(self.fit_functions)
        self.layout_bottom.addWidget(self.fit_button)
        self.layout_bottom.addWidget(self.save_fit_button)
        self.save_button = SaveButton(self.tree_widget, self.comment)
        self.layout_bottom.addWidget(self.save_button)
        self.compute_button.clicked.connect(self.tree_widget.compute)
        self.row_changed.connect(self.plot_widget.plot)
        self.changing_tree=False
        
        self.setLayout(self.layout_global)
        self.setGeometry(QRect(0, 0, 1000, 600))
        self.setMaximumHeight(600)
        self.show()
        self.move(0,0)
        self.plot_figure_options=dict({'marker':'-',
                                       'linewidth':2,
                                       'markersize':1,
                                       'xscale':1,
                                       'yscale':1,
                                       'xlabel':'Time (s)',
                                       'ylabel':'Value (a.u.)'})
        self.show_filters.setChecked(False)
    
    def update_project(self):
        SQLDatabase.set_project(self.current_project_widget.text())
        self.filter_widget.project_filter.item3.setText(self.current_project_widget.text())

class LegendItem(QHBoxLayout):
    
    def __init__(self, parent, item, color):
        super().__init__()
        self.widget=parent
        
        self.curve_id = int(item.data(0,0))
        self.name = item.data(1,0)
        self.date = item.data(2,0)
        self.text = QLabel('id: {:}'.format(self.curve_id))
        self.addWidget(self.text)
        self.text.setAutoFillBackground(True) # This is important!!
        self.color  = QtGui.QColor(color)#QColor(233, 10, 150)
        self.alpha  = 255
        values = "{r}, {g}, {b}, {a}".format(r = self.color.red(),
                                             g = self.color.green(),
                                             b = self.color.blue(),
                                             a = self.alpha
                                             )
        self.text.setStyleSheet("QLabel { background-color: rgba("+values+"); }")
        self.show_tick=QCheckBox('')
        self.show_tick.setChecked(True)
        self.addWidget(self.show_tick)
        self.addWidget(self.text)
        self.show_tick.stateChanged.connect(self.widget.update)
        
        self.plot_options_button=PlotFigureOptionButton(self,
                    elements=dict({'marker':[QComboBox,'-'],
                           'linewidth':[QLineEdit,'2'],
                           'markersize':[QLineEdit,'1'],
                           'color':[ColorPlotOption, color]}),
                    text='config')
        folder=os.path.split(inspect.getfile(Curve))[0]
        self.plot_options_button.setIcon((QtGui.QIcon(os.path.join(folder,
                                                            'pictures',
                                                            'gear.png'))))
        self.addWidget(self.plot_options_button)
        self.plot_options_button.optionsHaveChanged.connect(self.widget.update)
        
    def update(self):
        text=''
        if self.widget.config_id_tick.isChecked():
            text+='id: {:}'.format(self.curve_id)
        if self.widget.config_name_tick.isChecked():
            text+='name: {:}'.format(self.name)
        if self.widget.config_time_tick.isChecked():
            text+='time: {:}'.format(self.date)
        self.text.setText(text)
        self.color  = QtGui.QColor(self.plot_options_button.get_values()['color'])#QColor(233, 10, 150)
        self.alpha  = 255
        values = "{r}, {g}, {b}, {a}".format(r = self.color.red(),
                                             g = self.color.green(),
                                             b = self.color.blue(),
                                             a = self.alpha
                                             )
        self.text.setStyleSheet("QLabel { background-color: rgba("+values+"); }")
        

class LegendWidget(QWidget):
    
    def __init__(self, parent):
        super().__init__(parent)
        self.widget=QWidget()
        self.layout = QVBoxLayout()
        self.widget.setLayout(self.layout)
        #self.setMinimumSize(QSize(100,300))
        self.config_boxes=QHBoxLayout()
        self.layout.addLayout(self.config_boxes)
        #self.config_boxes.addWidget(QLabel('id'))
        self.config_id_tick=QCheckBox('id')
        self.config_boxes.addWidget(self.config_id_tick)
        self.config_id_tick.setChecked(True)
        self.config_name_tick=QCheckBox('name')
        self.config_boxes.addWidget(self.config_name_tick)
        self.config_time_tick=QCheckBox('time')
        self.config_boxes.addWidget(self.config_time_tick)
        self.general_plot_options=PlotFigureOptionButton(self,
                           elements=dict({
                           'xscale':[QLineEdit,'1'],
                           'yscale':[QLineEdit,'1'],
                           'xlabel':[QLineEdit,'Time (s)'],
                           'ylabel':[QLineEdit,'Value (a.u.)']}))
        folder=os.path.split(inspect.getfile(Curve))[0]
        self.general_plot_options.setIcon((QtGui.QIcon(os.path.join(folder,
                                                            'pictures',
                                                            'gear.png'))))
        self.config_boxes.addWidget(self.general_plot_options)
        self.setLayout(self.layout)
        self.chans=[]
        self.config_id_tick.stateChanged.connect(self.update)
        self.config_name_tick.stateChanged.connect(self.update)
        self.config_time_tick.stateChanged.connect(self.update)
    
    def add_curve(self, item, color, data):
        new_item=LegendItem(self, item, color)
        self.layout.addLayout(new_item)
        self.chans.append((new_item, data))
    
    def update(self):
        for item in self.chans:
            item[0].update()
            if item[0].show_tick.isChecked():
                item[1].show()
            else:
                item[1].hide()
            item[1].setPen(pg.mkPen(item[0].plot_options_button.get_values()['color']))
                
class PlotWindowContextMenu(QMenu):
    
    def __init__(self, parent, point, legend):
        super().__init__(parent)
        self.legend=legend
        self.plot_action=self.addAction('plot')
        self.plot_action.triggered.connect(self.plot)
        
        self.view_all_action=self.addAction('view all')
        self.view_all_action.triggered.connect(self.view_all)
        self.setFixedSize(self.sizeHint())
        self.setGeometry(parent.geometry().
                         translated(point))
        '''self.window_position.
                         translated(point)
                         .translated(self.window.param_widget.geometry().topLeft()))'''
        self.setVisible(True)
        self.show()
    
    def plot(self):
        items=self.parent().plot_widget.getPlotItem()
        window=self.parent().parent.tree_widget.window
        options=self.parent().legend.general_plot_options.get_values()
        plt.figure()
        #plt.title('id : {:}'.format(current_id))
        plt.xlabel(options.pop('xlabel'))
        plt.ylabel(options.pop('ylabel'))
        for chan in self.legend.chans:
            legend_item, data=chan
            item_options=legend_item.plot_options_button.get_values()
            color=legend_item.color
            alpha=legend_item.alpha
            if legend_item.show_tick.isChecked():
                
        #for i, item in enumerate(items.items):
                rect=data.viewRect()
                l, b, r, t = (rect.left(), rect.bottom(), 
                                          rect.right(), rect.top())
                
                x, y = data.getData()
                
                x*=float(options['xscale'])
                y*=float(options['yscale'])
                xmin, xmax=(np.min([l,r])*float(options['xscale']),
                            np.max([l,r])*float(options['xscale']))
                ymin, ymax=(np.min([b,t])*float(options['yscale']),
                            np.max([b,t])*float(options['yscale']))
                plt.plot(x,
                         y,
                         item_options['marker'],
                         markersize=item_options['markersize'],
                         linewidth=item_options['linewidth'],
                         color=item_options['color'],
                         label=legend_item.text.text())#options['color'])
                plt.xlim([xmin, xmax])
                plt.ylim([ymin, ymax])
            plt.legend()
            self.selected_items=self.parent().parent.tree_widget.window.tree_widget.selectedItems()
            curve_ids=[item.data(0,0) for item in self.selected_items]
            curve=Curve(curve_ids[0])
            plt.savefig(os.path.join(curve.get_or_create_dir(), 'display.png'), dpi=100)

    
    def view_all(self):
        self.parent().plot_widget.getPlotItem().enableAutoRange(enable=True)
        self.parent().plot_widget.getPlotItem().enableAutoRange(enable=False)
        
class PlotWindow(QWidget):
    
    COLORS = ['#1f77b4',
              '#ff7f0e',
              '#2ca02c',
              '#d62728',
              '#9467bd',
              '#8c564b',
              '#e377c2',
              '#7f7f7f',
              '#bcbd22',
              '#17becf']
    
    def __init__(self, plot_options, parent):
        super().__init__()
        self.parent=parent
        self.plot_options=plot_options
        self.layout_global = QHBoxLayout()
        self.plot_widget=pg.PlotWidget()
        self.legend=LegendWidget(self)
        self.layout_global.addWidget(self.plot_widget)
        self.layout_global.addWidget(self.legend)
        self.setLayout(self.layout_global)
        self.show()
        self.color_index=-1
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.contextMenu=None
        self.customContextMenuRequested.connect(self.RightClickMenu)
            
    def RightClickMenu(self, point):
        self.contextMenu=PlotWindowContextMenu(self, point, self.legend)
    
    def add_curve(self, item):
        self.color_index+=1
        color=self.COLORS[self.color_index%len(self.COLORS)]
        pen=pg.mkPen(color)
        self.plot_widget.getPlotItem().enableAutoRange(enable=True)
        curve_id = int(item.data(0,0))
        
        date = item.data(2,0)
        x,y,params=PlotWidget.get_data_and_params_from_date_and_id(date, curve_id)
        
        state=self.plot_options.currentText()
        if state=='dB':
            x_abs=x[np.abs(y)!=0]
            y_abs=y[np.abs(y)!=0]
            data=self.plot_widget.getPlotItem().plot(x_abs, 10*np.log10(np.abs(y_abs)), pen=pen)
        elif state=='Real':
            data=self.plot_widget.getPlotItem().plot(x, np.real(y), pen=pen)
        elif state=='Imaginary':
            data=self.plot_widget.getPlotItem().plot(x, np.imag(y), pen=pen)
        elif state=='Smith':
            data=self.plot_widget.getPlotItem().plot(np.real(y), np.imag(y), pen=pen)
        elif state=='Abs':
            data=self.plot_widget.getPlotItem().plot(x, np.abs(y), pen=pen)
        elif state=='Angle':
            data=self.plot_widget.getPlotItem().plot(x, np.angle(y), pen=pen)
        elif state=='FFT':
            data=self.plot_widget.getPlotItem().plot(np.fft.fftfreq(len(x), x[1]-x[0]),
                                    np.abs(np.fft.fft(y)**2/50/len(x)*(x[1]-x[0])), 
                                    pen=pen)
        self.plot_widget.getPlotItem().enableAutoRange(enable=False)
        
        self.legend.add_curve(item, color, data)

class ProjectLineEdit(QLineEdit):
    
    def __init__(self, item1):
        self.item1=item1
        super().__init__()
        
class NewFilterWidget(QGroupBox):
    
    def __init__(self, parent, filter_widget):
        super().__init__(parent=parent)
        self.parent=parent
        self.filter_widget=filter_widget
        self.global_layout=QGridLayout()
        self.setLayout(self.global_layout)
        self.item1=QComboBox()
        for column in Filter.columns:
            self.item1.addItem(column)
        self.global_layout.addWidget(self.item1, 0, 0)
        self.item2=QComboBox()
        for operation in ['<','<=','=','>','>=']:
            self.item2.addItem(operation)
        self.global_layout.addWidget(self.item2, 0, 1)
        self.item3=ProjectLineEdit(self.item1)
        self.global_layout.addWidget(self.item3, 0, 2)
        self.calendar=QCalendarWidget()
        self.global_layout.addWidget(self.calendar, 0 , 2)
        self.calendar.hide()
        self.remove_button=QToolButton()
        folder=os.path.split(inspect.getfile(Curve))[0]
        self.remove_button.setIcon(QtGui.QIcon(os.path.join(folder,
                                                            'pictures',
                                                            'minus.png')))
        self.global_layout.addWidget(self.remove_button, 0, 3)
        self.remove_button.clicked.connect(self.remove)
        self.activate_box = QCheckBox('activate')
        self.suggestion_list = QComboBox()
        self.global_layout.addWidget(self.suggestion_list, 1, 2)
        self.suggestion_list.hide()
        self.global_layout.addWidget(self.activate_box, 0, 4)
        self.item1.currentTextChanged.connect(self.column_changed)
        self.item3.textChanged.connect(self.text_changed)
        self.suggestion_list.currentIndexChanged.connect(self.selection_changed)
    
    def set_permanent(self):
        self.remove_button.hide()
    
    def selection_changed(self, text):
        self.item3.setText(self.suggestion_list.currentText())
    
    def text_changed(self, text):
        if self.item1.currentText()=='project':
            db=SQLDatabase()
            db.get_cursor()
            db.cursor.execute('''SELECT DISTINCT project FROM data WHERE position(%s in project)>0;''',
                              (text,))
            res=[k[0] for k in db.cursor.fetchall()]
            self.suggestion_list.currentIndexChanged.disconnect()
            self.suggestion_list.show()
            self.suggestion_list.clear()
            self.suggestion_list.addItem('')
            for item in res:
                self.suggestion_list.addItem(item)
            self.suggestion_list.currentIndexChanged.connect(self.selection_changed)
        elif self.item1.currentText()=='sample':
            db=SQLDatabase()
            db.get_cursor()
            db.cursor.execute('''SELECT DISTINCT sample FROM data WHERE position(%s in sample)>0;''',
                              (text,))
            res=[k[0] for k in db.cursor.fetchall()]
            self.suggestion_list.currentIndexChanged.disconnect()
            self.suggestion_list.show()
            self.suggestion_list.clear()
            self.suggestion_list.addItem('')
            for item in res:
                self.suggestion_list.addItem(item)
            self.suggestion_list.currentIndexChanged.connect(self.selection_changed)
        
    def column_changed(self, text):
        if text=='date':
            self.item3.hide()
            self.calendar.show()
            self.item2.clear()
            for operation in ['<','<=','=','>','>=']:
                self.item2.addItem(operation)
        elif text in ['name', 'project', 'sample']:
            self.calendar.hide()
            self.item2.clear()
            self.item3.show()
            for operation in ['=', 'contains']:
                self.item2.addItem(operation)
        else:
            self.calendar.hide()
            self.item3.show()
            self.item2.clear()
            for operation in ['<','<=','=','>','>=']:
                self.item2.addItem(operation)
        if text=='project':
            self.item3.clear()
            db=SQLDatabase()
            db.get_cursor()
            db.cursor.execute('''SELECT DISTINCT project FROM data;''')
            res=[k[0] for k in db.cursor.fetchall()]
            self.suggestion_list.show()
            self.suggestion_list.clear()
            self.suggestion_list.addItem('')
            for item in res:
                self.suggestion_list.addItem(item)
        elif text=='sample':
            self.item3.clear()
            db=SQLDatabase()
            db.get_cursor()
            db.cursor.execute('''SELECT DISTINCT sample FROM data;''')
            res=[k[0] for k in db.cursor.fetchall()]
            self.suggestion_list.show()
            self.suggestion_list.clear()
            self.suggestion_list.addItem('')
            for item in res:
                self.suggestion_list.addItem(item)
        
    def remove(self):
        for widget in [self.remove_button,self.item1,
                       self.item2, self.item3,
                       self.activate_box]:
            widget.hide()
            self.global_layout.removeWidget(widget)
        self.filter_widget.remove_filter(self)
        self.hide()
    
    def get_query(self):
        if self.item1.currentText() in ['id', 'parent', 'sample', 'project', 'name']:
            return Filter(self.item1.currentText(),
                          self.item2.currentText(),
                          self.item3.text())
        if self.item1.currentText()=='date':
            date=self.calendar.selectedDate()
            if self.item2.currentText() in ['<','>=']:
                t=datetime(date.year(), date.month(), date.day()).timestamp()
                return Filter(self.item1.currentText(),
                              self.item2.currentText(),
                              str(t))
            elif self.item2.currentText() in ['>','<=']:
                t=datetime(date.year(), date.month(), date.day()+1).timestamp()
                return Filter(self.item1.currentText(),
                              self.item2.currentText(),
                              str(t))
            elif self.item2.currentText()=='=':
                t1=datetime(date.year(), date.month(), date.day()).timestamp()
                t2=datetime(date.year(), date.month(), date.day()+1).timestamp()
                return [Filter(self.item1.currentText(),
                              '>',
                              str(t1)),
                        Filter(self.item1.currentText(),
                              '<',
                              str(t2))]

class MasterFilterWidget(QGroupBox):
    
    def __init__(self, window):
        super().__init__(parent=window)
        self.parent=window
        self.hide()
        #self.parent.add_filters.stateChanged.connect(self.set_visible)
        self.parent.show_filters.stateChanged.connect(self.show_widget)
        self.global_layout=QVBoxLayout()
        self.setLayout(self.global_layout)
        self.add_button=QToolButton()
        self.folder=os.path.split(inspect.getfile(Curve))[0]
        self.add_button.setIcon(QtGui.QIcon(os.path.join(self.folder,
                                                         'pictures',
                                                         'plus.png')))
        self.add_button.clicked.connect(self.add)
        self.global_layout.addWidget(self.add_button)
        self.filters=[]
        self.add()
        self.base_filter=self.filters[0]
        self.base_filter.set_permanent()
        self.base_filter.add()
        self.parent_filter=self.base_filter.filters[0]
        self.parent_filter.set_permanent()
        self.parent_filter.item1.setCurrentText('id')
        self.parent_filter.item2.setCurrentText('=')
        self.parent_filter.item3.setText('parent')
        self.parent_filter.activate_box.setChecked(True)
        self.base_filter.add()
        self.project_filter=self.base_filter.filters[1]
        self.project_filter.set_permanent()
        self.project_filter.item1.setCurrentText('project')
        self.project_filter.item2.setCurrentText('=')
        self.project_filter.item3.setText(SQLDatabase.get_project())
        self.project_filter.activate_box.setChecked(True)
        self.base_filter.activate_box.setChecked(True)
        
    
    def show_widget(self, state):
        if isinstance(state, bool):
            pass
        elif state==QtCore.Qt.Checked:
            self.show()
        elif state==QtCore.Qt.Unchecked:
            self.hide()
        else:
            pass

    def update_icon(self):
        if len(self.filters)==0:
            self.add_button.setIcon(QtGui.QIcon(os.path.join(self.folder,
                                                         'pictures',
                                                         'plus.png')))
        else:
            self.add_button.setIcon(QtGui.QIcon(os.path.join(self.folder,
                                                         'pictures',
                                                         'or.png')))
    
    def add(self):
        new_filter=FilterWidget(self)
        self.global_layout.addWidget(new_filter)
        new_filter.resize(10,10)
        self.filters.append(new_filter)
        self.update_icon()
        self.show()
    
    def remove_filter(self, filt):
        self.global_layout.removeWidget(filt)
        self.filters.remove(filt)
        self.update_icon()
    
    @property
    def at_least_one_check(self):
        if len(self.filters)==0:
            return False
        else:
            for f in self.filters:
                if f.at_least_one_check:
                    return True
            return False
    
    def get_query(self):
        queries, placeholders=[], []
        for f in self.filters:
            if f.at_least_one_check:
                if f.activate_box.isChecked():
                    query, placeholder=f.get_query()
                    queries.append(query)
                    for placeholder_item in placeholder:
                        placeholders.append(placeholder_item)
        if len(queries)>0:
            query = sql.SQL("SELECT id, childs, name, date, sample, project FROM data WHERE {fields} ORDER BY id DESC{offset}{firsts}")\
            .format(fields=sql.SQL(' OR ').join(queries),
                    offset=sql.Composed([sql.SQL(" OFFSET "),
                                         sql.Placeholder(),
                                         sql.SQL(" ROWS ")]),
                    firsts=sql.Composed([sql.SQL(" FETCH FIRST "),
                                         sql.Placeholder(),
                                         sql.SQL(" rows only")]))
        else:
            query = sql.SQL("SELECT id, childs, name, date, sample, project FROM data ORDER BY id DESC{offset}{firsts}")\
            .format(fields=sql.SQL(' OR ').join(queries),
                    offset=sql.Composed([sql.SQL(" OFFSET "),
                                         sql.Placeholder(),
                                         sql.SQL(" ROWS ")]),
                    firsts=sql.Composed([sql.SQL(" FETCH FIRST "),
                                         sql.Placeholder(),
                                         sql.SQL(" rows only")]))
        return query, placeholders

class FilterWidget(QGroupBox):
    
    def __init__(self, window):
        super().__init__(parent=window)
        self.parent=window
        self.global_layout=QVBoxLayout()
        self.setLayout(self.global_layout)
        self.toplayout=QHBoxLayout()
        self.global_layout.addLayout(self.toplayout)
        self.add_button=QToolButton()
        self.folder=os.path.split(inspect.getfile(Curve))[0]
        self.add_button.setIcon(QtGui.QIcon(os.path.join(self.folder,
                                                         'pictures',
                                                         'plus.png')))
        self.add_button.clicked.connect(self.add)
        self.toplayout.addWidget(self.add_button)
        self.remove_button=QToolButton()
        self.remove_button.setIcon(QtGui.QIcon(os.path.join(self.folder,
                                                            'pictures',
                                                            'minus.png')))
        self.toplayout.addWidget(self.remove_button)
        self.remove_button.clicked.connect(self.remove)
        self.activate_box = QCheckBox('activate')
        self.toplayout.addWidget(self.activate_box)
        self.filters=[]
    
    def set_permanent(self):
        self.remove_button.hide()
    
    def show_widget(self, state):
        if isinstance(state, bool):
            pass
        elif state==QtCore.Qt.Checked:
            self.show()
        elif state==QtCore.Qt.Unchecked:
            self.hide()
        else:
            pass
    
    def update_icon(self):
        if len(self.filters)==0:
            self.add_button.setIcon(QtGui.QIcon(os.path.join(self.folder,
                                                         'pictures',
                                                         'plus.png')))
        else:
            self.add_button.setIcon(QtGui.QIcon(os.path.join(self.folder,
                                                         'pictures',
                                                         'and.png')))
    
    def add(self):
        new_filter=NewFilterWidget(self.parent, self)
        self.global_layout.addWidget(new_filter)
        new_filter.resize(10,10)
        self.filters.append(new_filter)
        self.update_icon()
        self.show()
    
    def remove_filter(self, filt):
        self.global_layout.removeWidget(filt)
        self.filters.remove(filt)
        self.update_icon()
    
    def remove(self):
        for widget in [self.remove_button,
                       self.activate_box]:
            widget.hide()
            self.global_layout.removeWidget(widget)
        self.parent.remove_filter(self)
        self.hide()
    
    @property
    def at_least_one_check(self):
        if len(self.filters)==0:
            return False
        else:
            for f in self.filters:
                if f.activate_box.isChecked():
                    return True
            return False
    
    def get_query(self):
        filters=[]
        for f in self.filters:
            if f.activate_box.isChecked():
                res=f.get_query()
                if isinstance(res, list):
                    for q in res:
                       filters.append(q)
                else:
                    filters.append(res)
        placeholders=[f.item2 for f in filters if  f.placeholder]
        query = sql.SQL("({fields})").format(fields=sql.SQL(' AND ').join(filters))
        return query, placeholders

class Comment(QTextEdit):

    def __init__(self, treewidget):
        super().__init__()
        self.treewidget=treewidget
        self.setFixedHeight(30)
    
    def update(self, comment):
        self.setPlainText(comment)

class plotOptions(QComboBox):
    
    def __init__(self, treewidget):
        super().__init__()
        self.treewidget=treewidget
        self.addItems(['Real', 'Imaginary', 'dB', 'Smith', 'Abs', 'Angle', 'FFT'])
        self.currentTextChanged.connect(self.update)
    
    def update(self, new_text):
        self.window().plot_widget.plot()

class FitFunctions(QComboBox):
    
    def __init__(self, treewidget):
        super().__init__()
        self.treewidget=treewidget
        self.list=[k for k in Fit.__dict__.keys() if (not k.startswith('__') 
                    and not '_guess' in k)]
        self.addItems(self.list)
        self.treewidget.fit_function=self.list[0]
        self.currentTextChanged.connect(self.update)
    
    def update(self, new_text):
        self.treewidget.fit_function=new_text


class DirectoryButton(QPushButton):

    def __init__(self, treewidget):
        super().__init__()
        self.treewidget=treewidget
        self.current_id=None
        self.clicked.connect(self.action)

    def update(self, exists):
        if exists:
            self.setText('Go to directory')
        else:
            self.setText('Create directory')
    
    def startfile(self,filename):
        try:
            os.startfile(filename)
        except:
            subprocess.Popen(['xdg-open', filename])
    
    def action(self):
        self.current_id=self.window().tree_widget.active_item.data(0,0)
        date=self.window().tree_widget.active_item.data(2,0)
        if self.text()=='Create directory':
            folder=PlotWidget.get_folder_from_date(date)
            if not str(self.current_id) in os.listdir(folder):
                os.mkdir(os.path.join(folder,str(self.current_id)))
            self.setText('Go to directory')
        else:
            assert self.text()=='Go to directory'
            folder=PlotWidget.get_folder_from_date(date)
            assert str(self.current_id) in os.listdir(folder)
            self.startfile(os.path.join(folder,str(self.current_id)))

class PlotFigureButton(QPushButton):
    
    def __init__(self, treewidget, plotwidget):
        super().__init__()
        self.treewidget=treewidget
        self.plotwidget=plotwidget
        self.setText('Plot Figure')
        self.clicked.connect(self.action)
    
    def action(self):
        items=self.plotwidget.getPlotItem()
        current_id=self.treewidget.active_item.data(0,0)
        curve=Curve(current_id)
        for i, item in enumerate(items.items):
            rect=item.viewRect()
            l, b, r, t = (rect.left(), rect.bottom(), 
                                      rect.right(), rect.top())
            x, y = item.getData()
            options=self.window().plot_figure_options_button.get_values()
            plt.figure()
            plt.title('id : {:}'.format(current_id))
            plt.xlabel(options.pop('xlabel'))
            plt.ylabel(options.pop('ylabel'))
            #x*=float(options['xscale'])
            #y*=float(options['yscale'])
            xmin, xmax=(np.min([l,r])*float(options['xscale']),
                        np.max([l,r])*float(options['xscale']))
            ymin, ymax=(np.min([b,t])*float(options['yscale']),
                        np.max([b,t])*float(options['yscale']))
            plt.plot(x*float(options['xscale']),
                     y*float(options['yscale']),
                     options.pop('marker'),
                     markersize=options['markersize'],
                     linewidth=options['linewidth'],
                     color=options['color'])
            plt.xlim([xmin, xmax])
            plt.ylim([ymin, ymax])
            plt.savefig(os.path.join(curve.get_or_create_dir(), 'display.png'), dpi=100)

class ColorPlotOption(QLabel):
    
    def __init__(self, parent):
        super().__init__()
        self.parent=parent
        self.setAutoFillBackground(True)
    
    def get_color(self):
        return self.color.name()
        
    def set_color(self, color):
        self.color  = QtGui.QColor(color)
        values = "{r}, {g}, {b}, {a}".format(r = self.color.red(),
                                             g = self.color.green(),
                                             b = self.color.blue(),
                                             a = self.color.alpha()
                                             )
        self.setStyleSheet("QLabel { background-color: rgba("+values+"); }")
    
    def mouseDoubleClickEvent(self, event):
        self.choose_color()
        
    def choose_color(self):
        self.dialog=QColorDialog(self)
        self.dialog.setOption(QColorDialog.ShowAlphaChannel)
        self.dialog.colorSelected.connect(self.new_color)
        self.dialog.exec_()
    
    def new_color(self, color):
        self.set_color(color.name())
        self.parent.elements['color'][1]=color.name()
        
class PlotFigureOptionButton(QToolButton):
    
    optionsHaveChanged = QtCore.pyqtSignal()
    
    def __init__(self, parent, elements=dict({'marker':[QComboBox,'-'],
                           'linewidth':[QLineEdit,'2'],
                           'markersize':[QLineEdit,'1'],
                           'xscale':[QLineEdit,'1'],
                           'yscale':[QLineEdit,'1'],
                           'xlabel':[QLineEdit,'Time (s)'],
                           'ylabel':[QLineEdit,'Value (a.u.)'],
                           'color':[ColorPlotOption,'#921515']}),
                 text='Plot Figure options'):
        super().__init__()
        self.parent=parent
        self.setText(text)
        self.elements=elements
        self.widgets=dict().fromkeys(self.elements.keys())
        self.marker_dict=dict({'.':0,
                               '-':1})
        self.clicked.connect(self.action)
    
    def action(self):
        self.option_window=QWidget()
        self.layout=QGridLayout()
        self.option_window.setLayout(self.layout)
        for i, (key, val) in enumerate(self.elements.items()):
            self.widgets[key]=val[0](self)
            self.layout.addWidget(self.widgets[key] ,i , 0)
            self.layout.addWidget(QLabel(key),i , 1)
            if key=='marker':
                self.widgets[key].addItems(['.', '-'])
        self.set_default_values()
        
        N=len(self.elements.keys())
        
        self.confirm_button=QPushButton('confirm')
        self.layout.addWidget(self.confirm_button, N, 0)
        self.confirm_button.clicked.connect(self.confirm)
        self.option_window.show()
    
    def confirm(self):
        for i, (key, val) in enumerate(self.elements.items()):
            if val[0]==QLineEdit:
                self.elements[key][1]=self.widgets[key].text()
            elif val[0]==QComboBox:
                self.elements[key][1]=self.widgets[key].currentText()
        self.option_window.close()
        self.optionsHaveChanged.emit()
    
    def set_default_values(self):
        if 'marker' in self.elements.keys():
            marker_index=self.marker_dict[self.elements['marker'][1]]
            self.widgets['marker'].setCurrentIndex(marker_index)
        if 'color' in self.elements.keys():
            self.widgets['color'].set_color(self.elements['color'][1])
        for key, val in self.elements.items():
            if val[0]== QLineEdit:
                self.widgets[key].setText(val[1])
    
    def get_values(self):
        res=dict()
        for key, val in self.elements.items():
            res[key]=val[1]
        return res
        
class FitButton(QPushButton):
    
    def __init__(self, treewidget, plotwidget):
        super().__init__()
        self.treewidget=treewidget
        self.plotwidget=plotwidget
        self.setText('Fit')
        self.clicked.connect(self.action)
    
    def action(self):
        items=self.plotwidget.getPlotItem()
        current_id=self.treewidget.active_item.data(0,0)
        state=self.plotwidget.window().plot_options.currentText()
        curve=Curve(current_id)
        if state=='FFT':
            x, y=(np.fft.fftfreq(len(curve.x), curve.x[1]-curve.x[0]),
                            np.abs(np.fft.fft(curve.y))**2/50/len(curve.x)*(curve.x[1]-curve.x[0]))
        else:
            x, y=np.real(curve.x), curve.y
        for i, item in enumerate(items.items):
            rect=item.viewRect()
            l, r= (rect.left(), rect.right())
            xmin, xmax=np.min([l,r]), np.max([l,r])
            cond=np.logical_and(np.real(x)<xmax,
                                np.real(x)>xmin)
        y=y[cond]
        x=np.real(x[cond])
        self.fit_function=self.treewidget.fit_function
        state=self.plotwidget.window().plot_options.currentText()
        try:
            if state=='dB':
                self.fitparams, self.cov_x=Fit.fit(x,y, 
                                       function=self.fit_function,
                                       extract_covariance=True,
                                       to_minimize='log')
            elif state=='Abs':
                self.fitparams, self.cov_x=Fit.fit(x,np.abs(y), 
                                       function=self.fit_function,
                                       extract_covariance=True,
                                       to_minimize='log')
            else:
                self.fitparams, self.cov_x=Fit.fit(x,y, 
                                       function=self.fit_function,
                                       extract_covariance=True,
                                       to_minimize='linear')
            if hasattr(Fit, self.fit_function+'_keys'):
                self.keys=getattr(Fit, self.fit_function+'_keys')
            self.x_fit=np.linspace(np.min(x), np.max(x), 1000)
            self.y_fit=getattr(Fit, self.fit_function)(self.x_fit,
                         self.fitparams)
            fit_curve=self.plotwidget.fit_curve
            if fit_curve is not None:
                fit_curve.clear()
            
            if state=='dB':
                x_fit=self.x_fit[np.abs(self.y_fit)!=0]
                y_fit=self.y_fit[np.abs(self.y_fit)!=0]
                self.plotwidget.fit_curve=self.plotwidget.getPlotItem().plot(x_fit,
                                                          20*np.log10(y_fit),
                                                          pen=pg.mkPen('b'))
            elif state=='Real':
                self.plotwidget.fit_curve=self.plotwidget.\
                    getPlotItem().plot(self.x_fit, np.real(self.y_fit),
                                pen=pg.mkPen('b'))
            elif state=='Imaginary':
                self.plotwidget.fit_curve=self.plotwidget.getPlotItem()\
                        .plot(self.x_fit, np.imag(self.y_fit),
                              pen=pg.mkPen('b'))
            elif state=='Smith':
                self.plotwidget.fit_curve=self.plotwidget.getPlotItem()\
                    .plot(np.real(self.y_fit), np.imag(self.y_fit),
                          pen=pg.mkPen('b'))
            elif state=='Abs':
                self.plotwidget.fit_curve=self.plotwidget.getPlotItem()\
                    .plot(self.x_fit, np.abs(self.y_fit),
                          pen=pg.mkPen('b'))
            elif state=='Angle':
                self.plotwidget.fit_curve=self.plotwidget.getPlotItem()\
                    .plot(self.x_fit, np.angle(self.y_fit),
                          pen=pg.mkPen('b'))
            elif state=='FFT':
                self.plotwidget.fit_curve=self.plotwidget.getPlotItem()\
                    .plot(self.x_fit, np.real(self.y_fit),
                          pen=pg.mkPen('b'))
        except TypeError:
            pass

class SaveFitButton(QPushButton):
    
    def __init__(self, treewidget, plotwidget):
        super().__init__()
        self.treewidget=treewidget
        self.plotwidget=plotwidget
        self.setText('Save Fit')
        self.clicked.connect(self.action)
    
    def action(self):
        current_id=self.treewidget.active_item.data(0,0)
        curve=Curve(current_id)
        fitbutton=self.window().fit_button
        x,y=fitbutton.x_fit, fitbutton.y_fit
        fitparams=fitbutton.fitparams
        fitfunction=fitbutton.fit_function
        keys=fitbutton.keys
        params=dict({k: v for k,v in zip(keys, fitparams)})
        params_cov=dict({k+'_std': np.sqrt(fitbutton.cov_x[i][i]) for i, k in\
                         enumerate(keys)})
        curve.params.update(params)
        curve.save()
        fitcurve=Curve(x,y, name=fitfunction, **params, **params_cov)
        fitcurve.move(curve)

class SaveButton(QPushButton):

    def __init__(self, treewidget, comment):
        super().__init__()
        self.treewidget=treewidget
        self.comment=comment
        self.setText('Save comment')  
        self.clicked.connect(self.action)
    
    def action(self):
        if hasattr(self.treewidget, 'active_item'):
            current_id=self.treewidget.active_item.data(0,0)
            curve=Curve(current_id)
            curve.comment=self.comment.toPlainText()
            curve.save()

class QTreeContextMenu(QMenu):
    
    def __init__(self, item):
        super().__init__()
        self.item=item
        self.tree_widget=self.item.treeWidget()
        #self.move()
        self.item_position=self.tree_widget.visualItemRect(self.item)
        self.window_position=self.tree_widget.window.geometry()
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
        self.plot_action=self.addAction('plot')
        self.plot_action.triggered.connect(self.plot)
        self.edit_action=self.addAction('edit')
        self.edit_action.triggered.connect(self.edit)
        self.column_action=self.addAction('hide columns')
        self.column_action.triggered.connect(self.hide_columns)
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
            db=SQLDatabase()
            db.delete_entry(curve_id)
        self.tree_widget.compute()
    
    def plot(self):
        self.subplot_window=PlotWindow(self.tree_widget.window.plot_options, self)
        self.selected_items=self.tree_widget.selectedItems()
        selection=self.selected_items
        for item in selection:
            self.subplot_window.add_curve(item)
    
    def edit(self):
        self.selected_items=self.tree_widget.selectedItems()
        curve_ids=[item.data(0,0) for item in self.selected_items]
        db=SQLDatabase()
        metadatas=[db.get_name_sample_project(curve_id) for curve_id in curve_ids]
        self.window=EditCurveWindow(self, curve_ids, metadatas)
    
    def hide_columns(self):
        self.window=HideColumnWindow(self)

class HideColumnWindow(QWidget):
    
    def __init__(self, parent):
        super().__init__()
        
        self.setWindowTitle('Hide Columns')
        self.parent=parent
        self.layout=QGridLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel('Id'),0,0)
        self.hide_id=QCheckBox('')
        self.layout.addWidget(self.hide_id,0,1)
        
        self.layout.addWidget(QLabel('Name'),1,0)
        self.hide_name=QCheckBox('')
        self.layout.addWidget(self.hide_name,1,1)
        
        self.layout.addWidget(QLabel('Time'),2,0)
        self.hide_time=QCheckBox('')
        self.layout.addWidget(self.hide_time,2,1)
        
        self.layout.addWidget(QLabel('Sample'),3,0)
        self.hide_sample=QCheckBox('')
        self.layout.addWidget(self.hide_sample,3,1)
        
        self.layout.addWidget(QLabel('Project'),4,0)
        self.hide_project=QCheckBox('')
        self.layout.addWidget(self.hide_project,4,1)
        
        self.validate_button=QPushButton("Validate")
        self.layout.addWidget(self.validate_button, 5, 0, 1, 2)
        self.validate_button.clicked.connect(self.validate)
        
        self.dict_columns=dict({0:self.hide_id,
                                1:self.hide_name,
                                2:self.hide_time,
                                3:self.hide_sample,
                                4:self.hide_project})
        
        for key, val in self.dict_columns.items():
            val.setChecked(self.parent.tree_widget.isColumnHidden(key))
        self.setGeometry(QRect(20, 0, 300, 200))
        self.show()
    
    def keyPressEvent(self, event):
        if event.key() in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
            self.validate()
            
    def validate(self):
        for key, val in self.dict_columns.items():
            self.parent.tree_widget.setColumnHidden(key, val.isChecked())
        self.close()  
        
class EditCurveWindow(QWidget):
    
    def __init__(self, parent, curve_ids, metadatas):
        self.curve_ids=curve_ids
        super().__init__()
        self.setWindowTitle('Edit Curve')
        self.parent=parent
        self.global_layout=QVBoxLayout()
        self.setLayout(self.global_layout)
        hlayout=QHBoxLayout()
        self.global_layout.addLayout(hlayout)
        hlayout.addWidget(QLabel('Name'))
        self.name_edit=QLineEdit()
        hlayout.addWidget(self.name_edit)
        self.name_edit_confirmed=QCheckBox('should be edited')
        hlayout.addWidget(self.name_edit_confirmed)
        hlayout=QHBoxLayout()
        self.global_layout.addLayout(hlayout)
        hlayout.addWidget(QLabel('Sample'))
        self.sample_edit=QLineEdit()
        hlayout.addWidget(self.sample_edit)
        self.sample_edit_confirmed=QCheckBox('should be edited')
        hlayout.addWidget(self.sample_edit_confirmed)
        hlayout=QHBoxLayout()
        self.global_layout.addLayout(hlayout)
        hlayout.addWidget(QLabel('Project'))
        self.project_edit=QLineEdit()
        hlayout.addWidget(self.project_edit)
        self.project_edit_confirmed=QCheckBox('should be edited')
        hlayout.addWidget(self.project_edit_confirmed)
        if len(curve_ids)==1:
            name, sample, project=metadatas[0]
            self.name_edit.setText(name)
            self.sample_edit.setText(sample)
            self.project_edit.setText(project)
        self.validate_button=QPushButton("Validate")
        self.global_layout.addWidget(self.validate_button)
        self.validate_button.clicked.connect(self.validate)
        self.show()
    
    def keyPressEvent(self, event):
        if event.key() in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
            self.validate()
    
    def validate(self):
        name=self.name_edit.text()
        sample=self.sample_edit.text()
        project=self.project_edit.text()
        for curve_id in self.curve_ids:
            curve=Curve(curve_id)
            if self.name_edit_confirmed.isChecked():
                curve.name=name
            if self.project_edit_confirmed.isChecked():
                curve.project=project
            if self.sample_edit_confirmed.isChecked():
                curve.sample=sample
            curve.save()
        self.close()           
        
            
class QParamsContextMenu(QMenu):
    
    def __init__(self, point, window, current_param):
        super().__init__()
        self.window=window
        self.add_param_action=self.addAction("Add param")
        self.setVisible(True)
        self.current_param=current_param
        if self.current_param is not None:
            self.delete_param_action=self.addAction("Delete param")
        self.show()
        self.window_position=self.window.geometry()
        #self.header_position=self.item.treeWidget().header().geometry()
        self.setFixedSize(self.sizeHint())
        self.setGeometry(self.window_position.
                         translated(point)
                         .translated(self.window.param_widget.geometry().topLeft()))
        self.add_param_action.triggered.connect(self.add_param_menu)
        if self.current_param is not None:
            self.delete_param_action.triggered.connect(self.delete_param_menu)
    
    def add_param_menu(self):
        if hasattr(self.window.tree_widget, 'active_item'):
            item = self.window.tree_widget.active_item.data(0,0)
            if item is not None:
                self.add_param_window=NewParamWindow(self)
    
    def delete_param_menu(self):
        db=SQLDatabase()
        db.remove_param(self.window.tree_widget.active_item.data(0,0),
                         self.current_param)
        self.window.param_widget.actualize()
        self.close()
    
    def add_param(self, *args):
        if len(args)==1:
            name, value=args[0], 0
        else:
            name, value=args
        kwargs=dict({name:value})
        db=SQLDatabase()
        db.update_params(self.window.tree_widget.active_item.data(0,0),
                         **kwargs)
        self.window.param_widget.actualize()
        self.close()
                

class NewParamWindow(QWidget):
    
    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle('Add a parameter')
        self.parent=parent
        self.global_layout=QHBoxLayout()
        self.setLayout(self.global_layout)
        self.global_layout.addWidget(QLabel('Name'))
        self.name_edit=QLineEdit()
        self.global_layout.addWidget(self.name_edit)
        self.global_layout.addWidget(QLabel('Value'))
        self.value_edit=QLineEdit()
        self.validate_button=QPushButton("Validate")
        self.global_layout.addWidget(self.value_edit)
        self.global_layout.addWidget(self.validate_button)
        self.validate_button.clicked.connect(self.validate)
        self.show()
    
    def keyPressEvent(self, event):
        if event.key() in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
            self.validate()
    
    def validate(self):
        name=self.name_edit.text()
        value=self.value_edit.text()
        self.parent.add_param(name, value)
        self.close()
    

class ParamWidget(QTableWidget):
    
    def __init__(self, layout):
        super().__init__()
        self.setMouseTracking(True);
        self.viewport().setMouseTracking(True);
        self.layout=layout
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Param', 'Value'])
        self.verticalHeader().setVisible(False)
        self.setMaximumWidth(300)
        self.clicked_item=None
        self.previous_content=None
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.contextMenu=None
        self.customContextMenuRequested.connect(self.RightClickMenu)
        self.current_param=None
        self.cellEntered.connect(self.cellEnteredSlot)
        self.cellChanged.connect(self.cellChangedSlot)
    
    def cellEnteredSlot(self, row, column):
        self.current_param=self.item(row, 0).text()
    
    def cellChangedSlot(self, row, column):
        print('changed cell in {:} {:}'.format(self.item(row, 0).text(),
                                    self.item(row, 1).text()))
        if column==1:
            new_param=dict({self.item(row, 0).text():
                            self.item(row, 1).text()})
        else:
            new_param=dict()
            for row in range(self.rowCount()):
                new_param[self.item(row, 0).text()]=self.item(row, 1).text()
        item = self.window().tree_widget.active_item
        if item is not None:
            db=SQLDatabase()
            db.update_params(item.data(0,0),
                             **new_param)
            self.window().param_widget.actualize()
    
    def RightClickMenu(self, point):
        self.contextMenu=QParamsContextMenu(point, self.window(),
                                            self.current_param)
    
    def actualize(self, params=None):
        self.cellChanged.disconnect()
        item = self.window().tree_widget.active_item
        if item is not None:
            self.clear()
            self.setHorizontalHeaderLabels(['Param', 'Value'])
            if params is None:
                params=SQLDatabase().get_params(item.data(0,0))
                if 'comment' in params.keys():
                    params.pop('comment')
            self.setRowCount(len(params.keys()))
            for i,(k, v) in enumerate(params.items()):
                key = QTableWidgetItem()
                key.setText(k)
                self.setItem(i,0,key)
                value = QTableWidgetItem()
                value.setText(str(v))
                self.setItem(i,1,value)
        self.cellChanged.connect(self.cellChangedSlot)
    
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
        date=self.window().tree_widget.active_item.data(2,0)
        params=PlotWidget.get_params_from_date_and_id(date, current_id)
        params[name]=param
        folder=PlotWidget.get_folder_from_date(date)
        if not '{:}.h5'.format(current_id) in os.listdir(folder):
                print('the h5 file is nowhere to be found')
        else:
            with h5py.File(os.path.join(folder, '{:}.h5'.format(current_id)), 'r+') as f:
                data=f['data']
                for key, val in params.items():
                    if val is None:
                        data.attrs[key]='NONE'
                    elif isinstance(val, dict):
                        data.attrs[key]=json.dumps(val)
                    else:
                        data.attrs[key]=val
        self.new_param_window.close()


class TreeWidget(QTreeWidget):
    
    def __init__(self, window):
        super().__init__()
        self.window=window
        self.fit_function=None
        self.active_ID=None
        self.setColumnCount(5)
        self.length = np.min([SQLDatabase().get_n_keys(), N_ROW_DEFAULT])
        self.setHeaderLabels(['Id', 'Name', 'Date', 'Sample', 'Project'])
        for i in range(3):
            self.setColumnWidth(i,50)
        self.setColumnWidth(3,10)
        self.setColumnWidth(4,10)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.currentItemChanged.connect(self.current_item_changed)
        self.compute()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.contextMenu=None
        self.customContextMenuRequested.connect(self.RightClickMenu)
            
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
        self.window.row_changed.emit()
    
    def compute(self):
        new_size = self.window.spinbox_widget.value()
        offset = (self.window.page_number_spinbox.current_value-1)*new_size
        self.clear()
        database=SQLDatabase()
        query, placeholders=self.window.filter_widget.get_query()
        placeholders.append(offset)
        placeholders.append(new_size)
        
        hierarchy = database.get_all_hierarchy(query=query, placeholders=placeholders)
        if len(hierarchy)>0:
            for curve_id, childs, name, date, sample, project in hierarchy[0]:
                childs=json.loads(childs)
                item=QTreeWidgetItem()
                item.setData(0,0,curve_id)
                item.setData(2,0,time.strftime("%Y/%m/%d %H:%M:%S",time.localtime(float(date))))
                item.setData(1,0, name) 
                item.setData(3,0, sample)
                item.setData(4,0, project)
                if curve_id==self.active_ID:
                    self.setCurrentItem(item)
                self.addTopLevelItem(item)
                self.add_childs(item,hierarchy,childs,1)
        
    def add_childs(self, item, hierarchy, childs, level):
        if len(hierarchy)>level and len(childs)>0:
            keys=hierarchy[level]
            for child in childs:
                for key in keys:
                    if key[0]==child:
                        curve_id, gchilds, name, date, sample = key 
                        child_item=QTreeWidgetItem()
                        child_item.setData(0,0,str(curve_id))
                        child_item.setData(2,0,time.strftime("%Y/%m/%d %H:%M:%S",time.localtime(date)))
                        child_item.setData(1,0, name)
                        child_item.setData(3,0, sample)
                        gchilds=json.loads(gchilds)
                        if int(str(child))==self.active_ID:
                            self.setCurrentItem(child_item)
                        item.addChild(child_item)
                        self.add_childs(child_item, hierarchy, gchilds, level+1)
                        break


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
        
class PageNumberWidget(QSpinBox):
    
    def __init__(self):
        super().__init__()
        self.editingFinished.connect(self.editing_finished)
        self.setValue(1)
        self.current_value = self.value()
        self.setMaximumWidth(100)
        
        
    def editing_finished(self):
        self.current_value=self.value()
        self.window().pageno_changed.emit()

class PlotWidget(pg.PlotWidget):
    
    def __init__(self):
        super().__init__()
        self.fit_curve=None
            
    def plot(self):
        item = self.window().tree_widget.active_item
        if item is not None:
            self.getPlotItem().enableAutoRange(enable=True)
            curve_id = int(item.data(0,0))
            date = item.data(2,0)
            folder=PlotWidget.get_folder_from_date(date)
            x,y,params=PlotWidget.get_data_and_params_from_date_and_id(date, curve_id)
            self.getPlotItem().clear()
            
            state=self.window().plot_options.currentText()
            if state=='dB':
                x_abs=x[np.abs(y)!=0]
                y_abs=y[np.abs(y)!=0]
                self.getPlotItem().plot(x_abs, 10*np.log10(np.abs(y_abs)))
            elif state=='Real':
                self.getPlotItem().plot(x, np.real(y))
            elif state=='Imaginary':
                self.getPlotItem().plot(x, np.imag(y))
            elif state=='Smith':
                self.getPlotItem().plot(np.real(y), np.imag(y))
            elif state=='Abs':
                self.getPlotItem().plot(x, np.abs(y))
            elif state=='Angle':
                self.getPlotItem().plot(x, np.angle(y))
            elif state=='FFT':
                self.getPlotItem().plot(np.fft.fftfreq(len(x), x[1]-x[0]),
                                        np.abs(np.fft.fft(y)**2/50/len(x)*(x[1]-x[0])))
            self.getPlotItem().enableAutoRange(enable=False)
            if 'comment' in params.keys():
                comment=params.pop('comment')
            else:
                comment=''
            self.window().param_widget.actualize(params)
            exists=os.path.exists(os.path.join(folder, '{:}'.format(curve_id)))
            self.window().directory_button.update(exists)
            self.window().comment.update(comment)
    
    @staticmethod
    def get_folder_from_date(date):
        t=time.mktime(time.strptime(date,"%Y/%m/%d %H:%M:%S"))
        path = os.path.join(SQLDatabase.get_config()['data_location'],
                            time.strftime("%Y",time.gmtime(t)),
                            time.strftime("%m",time.gmtime(t)),
                            time.strftime("%d",time.gmtime(t)))
        if not os.path.exists(path):
            print("the folder is nowhere to be found...")
        return path
    
    @staticmethod
    def get_data_and_params_from_date_and_id(date, curve_id):
        folder=PlotWidget.get_folder_from_date(date)
        if not '{:}.h5'.format(curve_id) in os.listdir(folder):
                print('the h5 file is nowhere to be found')
                return [], [], dict()
        else:
            with h5py.File(os.path.join(folder, '{:}.h5'.format(curve_id)), 'r') as f:
                    data=f['data']
                    x=np.real(data[0])
                    y=data[1]
                    params=dict()
                    params=PlotWidget.extract_dictionary(params, data.attrs)
            return x,y,params
    
    @staticmethod
    def get_params_from_date_and_id(date, curve_id):
        folder=PlotWidget.get_folder_from_date(date)
        if not '{:}.h5'.format(curve_id) in os.listdir(folder):
                print('the h5 file is nowhere to be found')
        else:
            with h5py.File(os.path.join(folder, '{:}.h5'.format(curve_id)), 'r') as f:
                    data=f['data']
                    params=dict()
                    params=PlotWidget.extract_dictionary(params, data.attrs)
            return params
    
    @staticmethod
    def extract_dictionary(res, obj):
        for key, val in obj.items():
            if val=='NONE':
                res[key]=None
            elif isinstance(val, str) and val.startswith('{'):
                res[key]=json.loads(val)
            else:
                res[key]=val
        return res

app = QtCore.QCoreApplication.instance()
if app is None:
    app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(True)
window = WindowWidget()
app.exec_()


