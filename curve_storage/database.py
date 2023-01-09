import os, json, time, shutil
import numpy as np
import h5py, sys
import shutil
from psycopg2 import sql, connect, InterfaceError
from contextlib import contextmanager
from PyQt5.QtWidgets import (QFileDialog, QApplication, QWidget, QCheckBox,
                             QLineEdit, QVBoxLayout, QLabel,
                             QPushButton, QCalendarWidget, QHBoxLayout)
import PyQt5.QtCore as QtCore
from PyQt5.QtGui import QTextCharFormat, QPalette
from setuptools import distutils

DATABASE_NAME='postgres'
USER='postgres'
DATABASE_HOST=r'quarpi.qopt.nbi.dk'
PORT='5432'
ROOT=os.path.expanduser('~')


@contextmanager
def transaction(conn):
    # We must issue a "BEGIN" explicitly when running in auto-commit mode.
    #conn.execute('BEGIN')
    try:
        # Yield control back to the caller.
        yield
    except:
        conn.rollback()  # Roll back all changes if an exception occurs.
        raise
    else:
        if not conn.closed:
            conn.commit()

class Filter(sql.Composed):
    
    columns=["parent", "id", "name", "date", "sample", "project"]
    
    def __init__(self, item1, relation, item2):
        if relation!='contains':
            self.item1=sql.Identifier(item1)
            self.relation=sql.SQL(relation)
            if item2 not in Filter.columns:
                self.placeholder=True
                self.item2=item2
                super().__init__([self.item1,
                                 self.relation,
                                 sql.Placeholder()])
            else:
               self.placeholder=False
               self.item2=sql.Identifier(item2)
               super().__init__([self.item1,
                                 self.relation,
                                 self.item2])
        else:
            self.placeholder=True
            self.init=sql.SQL("position(")
            self.item1=sql.Identifier(item1)
            self.item2=item2
            junction=sql.SQL("in ")
            end=sql.SQL(") > 0")
            super().__init__([self.init,
                              sql.Placeholder(),
                              junction, 
                              self.item1,
                              end])
class Calendar(QCalendarWidget):
    
    
    def __init__(self):
        super().__init__()
        self.from_date=None
        self.to_date=None
        self.highlighter=QTextCharFormat()
        self.highlighter.setBackground(
            self.palette().brush(QPalette.Highlight))
        self.highlighter.setForeground(
            self.palette().brush(QPalette.HighlightedText))
        self.keylist=[]
        self.clicked.connect(self.select_Date_range)
        
    def keyPressEvent(self, event):
        astr = event.key()
        self.keylist.append(astr)

    def keyReleaseEvent(self, event):
        del self.keylist[-1]
    
    def select_Date_range(self, date_value):
        self.highlight_range(QTextCharFormat())
        if ((QtCore.Qt.Key_Shift in self.keylist) & 
            (self.from_date is not None)):
            self.to_date=date_value
            self.highlight_range(self.highlighter)
        else:
            self.from_date=date_value
            self.to_date=None
        
    def highlight_range(self, format):
        if (self.from_date is not None and 
            self.to_date is not None):
            d1=min([self.from_date, self.to_date])
            d2=max([self.from_date, self.to_date])
            while (d1<=d2):
                self.setDateTextFormat(d1, format)
                d1=d1.addDays(1)
                
        
class CopyDatabaseWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Database Copy')
        self.layout=QVBoxLayout(self)
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel('source host'))
        self.source_host=QLineEdit(DATABASE_HOST)
        self.layout.addWidget(self.source_host)
        self.layout.addWidget(QLabel('source user'))
        self.source_user=QLineEdit(USER)
        self.layout.addWidget(self.source_user)
        self.layout.addWidget(QLabel('source port'))
        self.source_port=QLineEdit(PORT)
        self.layout.addWidget(self.source_port)
        self.target_host=QLineEdit('localhost')
        self.layout.addWidget(QLabel('source database'))
        self.source_database=QLineEdit(DATABASE_NAME)
        self.layout.addWidget(self.source_database)
        self.layout.addWidget(QLabel('source password'))
        self.source_password=QLineEdit()
        self.source_password.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.source_password)
        self.layout.addWidget(QLabel('set source data path'))
        self.source_datapath=QLineEdit()
        self.select_source_datapath=QPushButton('Browse')
        self.select_source_datapath_layout=QHBoxLayout()
        self.select_source_datapath_layout.addWidget(self.source_datapath)
        self.select_source_datapath_layout.addWidget(self.select_source_datapath)
        self.select_source_datapath.clicked.connect(self.browse_source_datapath)
        self.layout.addLayout(self.select_source_datapath_layout)
        self.layout.addWidget(QLabel('target host'))
        self.layout.addWidget(self.target_host)
        self.layout.addWidget(QLabel('target user'))
        self.target_user=QLineEdit(USER)
        self.layout.addWidget(self.target_user)
        self.layout.addWidget(QLabel('target port'))
        self.target_port=QLineEdit(PORT)
        self.layout.addWidget(self.target_port)
        self.layout.addWidget(QLabel('target database'))
        self.target_database=QLineEdit(DATABASE_NAME)
        self.layout.addWidget(self.target_database)
        self.layout.addWidget(QLabel('target password'))
        self.target_password=QLineEdit()
        self.target_password.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.target_password)
        self.layout.addWidget(QLabel('set target data path'))
        self.target_datapath=QLineEdit()
        self.select_target_datapath=QPushButton('Browse')
        self.select_target_datapath_layout=QHBoxLayout()
        self.select_target_datapath_layout.addWidget(self.target_datapath)
        self.select_target_datapath_layout.addWidget(self.select_target_datapath)
        self.select_target_datapath.clicked.connect(self.browse_target_datapath)
        self.layout.addLayout(self.select_target_datapath_layout)
        self.layout.addWidget(QLabel('set period'))
        self.calendar=Calendar()
        self.layout.addWidget(self.calendar)
        self.reload=QCheckBox('transfer again the data already here?')
        self.reload.setChecked(False)
        self.layout.addWidget(self.reload)
        self.accept=QPushButton('Confirm transfer')
        self.layout.addWidget(self.accept)
        self.accept.clicked.connect(self.confirm)
    
    def browse_target_datapath(self):
        data_location=QFileDialog.getExistingDirectory(
            caption='select the target root directory of the data')
        self.target_datapath.setText(str(data_location))
    
    def browse_source_datapath(self):
        data_location=QFileDialog.getExistingDirectory(
            caption='select the source root directory of the data')
        self.source_datapath.setText(str(data_location))
    
    def confirm(self):
        t_ini=time.mktime(self.calendar.from_date.toPyDate().timetuple())
        t_end=time.mktime(self.calendar.to_date.toPyDate().timetuple())+3600*24
        self.db1=SQLDatabase(db=connect(host=self.source_host.text(),
                         database=self.source_database.text(),
                         user=self.source_user.text(),
                         password=self.source_password.text()),
                             data_location=self.source_datapath.text())
        res=self.db1.get_all_data_in_period(t_ini, t_end)
        self.db2=SQLDatabase(db=connect(host=self.target_host.text(),
                         database=self.target_database.text(),
                         user=self.target_user.text(),
                         password=self.target_password.text()),
                             data_location=self.target_datapath.text())
        print('transferring the database...')
        self.db2.add_entry(res)
        print('database is transferred.')
        N=len(res)
        print('transferring the data, {:} curves to consider'.format(N))
        for i, item in enumerate(res):
            if i%10==0:
                print('{:.2f}% done'.format(float(i)*100/N))
            curve_id=int(item[0])
            
            date=item[2]
            filename='{:}.h5'.format(curve_id)
            dir1=self.db1.get_folder_from_date(date)
            dir2=self.db2.get_folder_from_date(date)
            if self.reload.isChecked() or not os.path.exists(
                    os.path.join(dir2,
                                 filename)):
                distutils.file_util.copy_file(os.path.join(dir1,
                                         filename),
                            os.path.join(dir2,
                                         filename),
                            update=1)
                if str(curve_id) in os.listdir(dir1):
                    distutils.dir_util.copy_tree(os.path.join(dir1,
                                         str(curve_id)),
                                    os.path.join(dir2,
                                         str(curve_id)),
                                    update=1)
        self.db1.close()
        self.db2.close()
        self.close()
    
class setConfigWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Database Config')
        self.layout=QVBoxLayout(self)
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel('host'))
        self.host=QLineEdit(DATABASE_HOST)
        self.layout.addWidget(self.host)
        self.layout.addWidget(QLabel('user'))
        self.user=QLineEdit(USER)
        self.layout.addWidget(self.user)
        self.layout.addWidget(QLabel('port'))
        self.port=QLineEdit(PORT)
        self.layout.addWidget(self.port)
        self.layout.addWidget(QLabel('database'))
        self.database=QLineEdit(DATABASE_NAME)
        self.layout.addWidget(self.database)
        self.layout.addWidget(QLabel('source password'))
        self.password=QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.password)
        self.layout.addWidget(QLabel('set data path'))
        self.datapath=QLineEdit()
        self.select_datapath=QPushButton('Browse')
        self.select_datapath_layout=QHBoxLayout()
        self.select_datapath_layout.addWidget(self.datapath)
        self.select_datapath_layout.addWidget(self.select_datapath)
        self.select_datapath.clicked.connect(self.browse_datapath)
        self.layout.addLayout(self.select_datapath_layout)
        self.accept=QPushButton('Confirm')
        self.layout.addWidget(self.accept)
        self.accept.clicked.connect(self.confirm)
    
    def browse_datapath(self):
        data_location=QFileDialog.getExistingDirectory(
            caption='select the root directory of the data')
        self.datapath.setText(str(data_location))
    
    def confirm(self):
        with open(os.path.join(ROOT, 'database_config.json'), 'w') as f:
            res=dict({'data_location':self.datapath.text(),
                      'database_host':self.host.text(),
                      'database_name':self.database.text(),
                      'user':self.user.text(),
                      'password':self.password.text(),
                      'port':self.port.text()})
            json.dump(res, f)
        self.close()
     
class SQLDatabase():
    
    first_instance = True
    instances = []
    
    @staticmethod
    def set_config():
        
        app = QtCore.QCoreApplication.instance()
        app.setQuitOnLastWindowClosed(True)
        widget=setConfigWidget()
        widget.show()
        app.exec_()
    
    @staticmethod
    def get_config():
        with open(os.path.join(ROOT, 'database_config.json'), 'r') as f:
            return json.load(f)
    
    def __init__(self, data_location=None, db=None):
        if db is None:
            if not 'database_config.json' in os.listdir(ROOT):
                SQLDatabase.set_config()
            config=SQLDatabase.get_config()
            for k,v in config.items():
                setattr(self, k, v)
            
            if not self.__class__.first_instance:
                self.db=self.__class__.instances[0]
            else:
                self.__class__.first_instance=False
                self.db=connect(host=self.database_host,
                                 database=self.database_name,
                                 user=self.user,
                                 password=self.password)
                if not self.is_table_created():
                    self.create_table()
                self.__class__.instances.append(self.db)
        else:
            self.db=db
            self.data_location=data_location
            self.__class__.instances = [self.db]
            if not self.is_table_created():
                    self.create_table()
            
    
    def create_local_copy(self):
        app = QtCore.QCoreApplication.instance()
        if app is None:
           app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(True)
        widget=CopyDatabaseWidget()
        widget.show()
        app.exec_()
    
    def get_all_data_in_period(self, t_ini, t_end):
        self.get_cursor()
        self.cursor.execute('''SELECT id, name, date, childs, parent, project, sample FROM data WHERE date>%s AND date<%s;''',
                            (t_ini, t_end,))
        return self.cursor.fetchall()
    
    def get_all_ids(self):
        if self.is_table_created():
            self.get_cursor()
            self.cursor.execute('''SELECT id FROM data;''')
            return np.array(self.cursor.fetchall()).flatten().tolist()
        else:
            return []
    
    def get_one_id(self):
        self.get_cursor()
        self.cursor.execute('''SELECT id FROM data;''')
        return np.array(self.cursor.fetchone()).flatten()[0]
    
    def get_highest_key(self):
        self.get_cursor()
        self.cursor.execute('''SELECT max(id) FROM data;''')
        return int(self.cursor.fetchone()[0])
    
    def get_new_id(self):
        self.get_cursor()
        self.cursor.execute('''SELECT nextval(%s);''', ('public.curve_id_seq',))
        return int(self.cursor.fetchone()[0])
    
    def get_all_hierarchy(self, query=None, placeholders=None):
        self.get_cursor()
        if query is None:
            self.cursor.execute('''SELECT id, childs, name, date, sample FROM data WHERE id=parent ORDER BY id DESC''')
        else:
            self.cursor.execute(query, placeholders)
        res=self.cursor.fetchall()
        hierarchy=[res]
        childs=[]
        for k in res:
            childs+=json.loads(k[1])
        while(len(childs)>0):
            self.cursor.execute('''SELECT id, childs, name, date, sample FROM data WHERE id=ANY(%s) ORDER BY id DESC;''',
                              (childs,))
            res=self.cursor.fetchall()
            hierarchy.append(res)
            childs=[]
            for k in res:
                childs+=json.loads(k[1])
        return hierarchy
    
    def get_name_and_time(self, curve_id):
        self.get_cursor()
        if not isinstance(curve_id, list) and not(isinstance(curve_id, tuple)):
            self.cursor.execute('''SELECT id, name, date FROM data WHERE id=%s''', (int(curve_id),))
            return self.cursor.fetchone()
        elif isinstance(curve_id, list) and len(curve_id)==1:
            self.cursor.execute('''SELECT id, name, date FROM data WHERE id=%s''', (int(curve_id[0]),))
            return self.cursor.fetchall()
        else:
            self.cursor.execute('''SELECT id, name, date FROM data WHERE id = ANY (%s);''',(curve_id,))
            return self.cursor.fetchall()
    
    def get_name_and_time_and_sample(self, curve_id):
        self.get_cursor()
        if not isinstance(curve_id, list) and not(isinstance(curve_id, tuple)):
            self.cursor.execute('''SELECT id, name, date, sample FROM data WHERE id=%s''', (int(curve_id),))
            return self.cursor.fetchone()
        elif isinstance(curve_id, list) and len(curve_id)==1:
            self.cursor.execute('''SELECT id, name, date, sample FROM data WHERE id=%s''', (int(curve_id[0]),))
            return self.cursor.fetchall()
        else:
            self.cursor.execute('''SELECT id, name, date, sample FROM data WHERE id = ANY (%s);''',(curve_id,))
            return self.cursor.fetchall()
    
    def get_cursor(self):
        try:
            self.cursor=self.db.cursor()
        except InterfaceError:
            self.db=connect(host=self.database_host,
                             database=self.database_name,
                             user=self.user)
            self.__class__.instances=[self.db]
            self.cursor=self.db.cursor()
    
    def get_n_keys(self):
        self.get_cursor()
        self.cursor.execute('''SELECT count(id) FROM data;''')
        return self.cursor.fetchall()[0][0]
        
    def is_table_created(self):
        with transaction(self.db):
            self.get_cursor()
            self.cursor.execute('''SELECT
                    table_schema || '.' || table_name
                    FROM
                    information_schema.tables
                    WHERE
                    table_type = 'BASE TABLE'
                    AND
                    table_schema NOT IN ('pg_catalog', 'information_schema');
                    ''')
            return ('public.data',) in self.cursor.fetchall()
    
    def create_table(self):
        with transaction(self.db):
            self.get_cursor()
            self.cursor.execute('''
                           CREATE TABLE data(id INTEGER PRIMARY KEY, name TEXT,
                           date FLOAT, childs TEXT, parent INTEGER,
                           project text, sample text);
                           ''')
        
    
    def save(self, curve):
        if curve.id is None:
            self.add_entry(curve)
        else:
            self.update_entry(curve)
        
    def add_entry(self, curve):
        if isinstance(curve, Curve):
            assert curve.id is None
            curve_id = self.get_new_id()
            curve.id=curve_id
            try:
                curve.date
            except AttributeError:
                curve.date=time.time()
            if curve.parent is None:
                curve.parent=curve.id
                with transaction(self.db):
                    self.get_cursor()
                    self.cursor.execute('''INSERT INTO data(id, name, date, childs, parent, project, sample)
                          VALUES(%s,%s,%s,%s,%s,%s,%s);''',
                          (int(curve_id),
                          curve.name,
                          float(curve.date),
                          json.dumps(curve.childs),
                          int(curve.parent),
                          curve.project,
                          curve.sample))
            curve.directory = self.get_folder_from_date(curve.date)
            curve.parent = curve_id
        elif isinstance(curve, list):
            if isinstance(curve[0], tuple):
                with transaction(self.db):
                    self.get_cursor()
                    args_str = b','.join(self.cursor.mogrify("(%s,%s,%s,%s,%s,%s,%s)", x) for x in curve)
                    self.cursor.execute('''INSERT INTO data(id, name, date, childs, parent, project, sample)
                                        VALUES ''' + args_str.decode() + 
                                        ''' ON CONFLICT (id) DO UPDATE SET name=data.name'''+
                                        ''', parent=data.parent, childs=data.childs,'''+
                                        ''' project=data.project, sample=data.sample;''') 
        
    
    def extract_dictionary(self, res, obj):
        for key, val in obj.items():
            if val=='NONE':
                res[key]=None
            elif isinstance(val, str) and val.startswith('{'):
                res[key]=json.loads(val)
            else:
                res[key]=val
        return res
    
    
    def get_curve(self, *args):
        '''
        retrieve a curve. 
        -With a single scalar argument, return the Curve object with the id equal to this argument.
        -With a list of scalar argument, return a list of Curve objects with the ids equal to the list members
        -With a list of scalar as a first argument, and a string as a second argument, return a list of all the Curve objects
        whose names match the string and whose ids belong to the list
        '''
        if (len(args)>=1 and np.isscalar(args[0])):
            curve_id=args[0]
            if self.exists(curve_id):
                self.get_cursor()
                self.cursor.execute('''SELECT name, date, childs, parent, project, sample FROM data WHERE id=%s;''', (int(curve_id),))
                res = self.cursor.fetchone()
                name = res[0]
                date = float(res[1])
                childs = json.loads(res[2])
                parent = int(res[3])
                params = dict()
                project = res[4]
                sample = res[5]
                directory=self.get_folder_from_date(date)
                if os.path.exists(os.path.join(directory, '{:}.h5'.format(curve_id))):
                    with h5py.File(os.path.join(directory, '{:}.h5'.format(curve_id)), 'r') as f:
                        data=f['data']
                        x=data[0]
                        y=data[1]
                        params=self.extract_dictionary(params, data.attrs)
                    return Curve(curve_id, x, y, database=self, name=name,
                                 date=date, childs=childs, parent=parent,
                                 params=params, directory=directory,
                                 project=project, sample=sample)
                else:
                    return Curve(curve_id, [], [], database=self, name=name, 
                                 date=date, childs=childs, parent=parent, 
                                 params=params, directory=directory,
                                 project=project, sample=sample)
            else:
                return None
        elif len(args)==1 and isinstance(args[0], list):
            curve_ids=args[0]
            if  len(curve_ids)==0:
                return []
            elif len(curve_ids)==1:
                return [self.get_curve(curve_ids[0])]
            else:
                self.get_cursor()
                self.cursor.execute('''SELECT id, name, date, childs, parent, project, sample FROM data WHERE id=ANY(%s) ORDER BY id ASC;''',(curve_ids,))
                res=[]
                for data in self.cursor.fetchall():
                    curve_id = int(data[0])
                    name = data[1]
                    date = float(data[2])
                    childs = json.loads(data[3])
                    parent = int(data[4])
                    params = dict()
                    project = data[5]
                    sample = data[6]
                    directory=self.get_folder_from_date(date)
                    if os.path.exists(os.path.join(directory, '{:}.h5'.format(curve_id))):
                        with h5py.File(os.path.join(directory, '{:}.h5'.format(curve_id)), 'r') as f:
                            data=f['data']
                            x=data[0]
                            y=data[1]
                            params=self.extract_dictionary(params, data.attrs)
                        res.append(Curve(curve_id, x, y, database=self, name=name,
                                     date=date, childs=childs, parent=parent,
                                     params=params, directory=directory,
                                     project=project, sample=sample))
                    else:
                        res.append(Curve(curve_id, [], [], database=self, name=name, 
                                     date=date, childs=childs, parent=parent, 
                                     params=params, directory=directory,
                                     project=project, sample=sample))
                return res
        elif len(args)==2:
            if len(args[0])==1:
                return self.get_curve(args[0][0])
            else:
                curve_ids, name=args
                assert isinstance(curve_ids, list)
                curve_ids=[int(cid) for cid in curve_ids]
                assert isinstance(name, str)
                self.get_cursor()
                self.cursor.execute('''SELECT id, date, childs, parent, project, sample FROM data WHERE id=ANY(%s) AND name=%s;''',
                                    (args[0], name))
                results=self.cursor.fetchall()
                curves=[]
                if results is not None:
                    for res in results:
                        curve_id = int(res[0])
                        date = float(res[1])
                        childs = json.loads(res[2])
                        parent = int(res[3])
                        params = dict()
                        project = res[4]
                        sample = res[5]
                        directory=self.get_folder_from_date(date)
                        if os.path.exists(os.path.join(directory, '{:}.h5'.format(curve_id))):
                            with h5py.File(os.path.join(directory, '{:}.h5'.format(curve_id)), 'r') as f:
                                data=f['data']
                                x=data[0]
                                y=data[1]
                                params=self.extract_dictionary(params, data.attrs)
                            curves.append(Curve(curve_id, x, y, database=self, name=name,
                                         date=date, childs=childs, parent=parent,
                                         params=params, directory=directory,
                                         project=project, sample=sample))
                        else:
                            curves.append(Curve(curve_id, [], [], database=self, name=name, 
                                         date=date, childs=childs, parent=parent, 
                                         params=params, directory=directory,
                                         project=project, sample=sample))
                else:
                    print('no curves with this name were found')
                return curves
            
    def get_curve_metadata(self, curve_id):
        if self.exists(curve_id):
            self.get_cursor()
            self.cursor.execute('''SELECT name, date, childs, parent, sample FROM data WHERE id=%s;''', (int(curve_id),))
            res = self.cursor.fetchone()
            name = res[0]
            date = float(res[1])
            childs = json.loads(res[2])
            parent = int(res[3])
            sample = res[4]
            return name, date, childs, parent, sample
        else:
            return None
    
    def get_subhierarchy(self, curve_id, res=None):
        childs=self.get_childs(curve_id)
        if res is None:
            res=dict({curve_id:childs})
            res=self.get_subhierarchy(childs, res=res)
        else:
            for cid, child in childs:
                res[cid]=child
                res=self.get_subhierarchy(child, res=res)
        return res
    
    def _get_full_subhierarchy_recursive(self, res, child_dict, data_dict):
        for k in res.keys():
            res[k]['childs']=[]
            for child in child_dict[k]:
                res[k]['childs'].append(self._get_full_subhierarchy_recursive(
                        dict({child:data_dict[child]}),
                        child_dict,
                        data_dict))
        return res
    
    def get_full_subhierarchy(self, curve_id):
        child_dict=self.get_subhierarchy(curve_id)
        datas=self.get_name_and_time_and_sample(list(child_dict.keys()))
        data_dict=dict()
        for cid, name, t, sample in datas:
            directory=self.get_folder_from_date(float(t))
            filename=os.path.join(directory, '{:}.h5'.format(int(cid)))
            with h5py.File(filename, 'r') as f:
                            data=f['data']
                            x=data[0]
                            y=data[1]
                            params=self.extract_dictionary(dict(), data.attrs)
            data_dict[cid]=dict({'x':x,
                                     'y':y,
                                     'params':params,
                                     'timestamp':float(t),
                                     'name':name,
                                     'sample':sample})
        return self._get_full_subhierarchy_recursive(
                dict({curve_id:data_dict[curve_id]}),
                child_dict, data_dict)
        
    
    def get_curve_childs_and_parent(self, curve_id):
        if self.exists(curve_id):
            self.get_cursor()
            self.cursor.execute('''SELECT childs, parent FROM data WHERE id=%s;''', (int(curve_id),))
            res = self.cursor.fetchone()
            childs = json.loads(res[0])
            parent = int(res[1])
            return childs, parent
        else:
            return None
    
    def get_params(self, curve_id):
        if self.exists(curve_id):
            folder=self.get_folder_from_id(curve_id)
            filename=os.path.join(folder, '{:}.h5'.format(int(curve_id)))
            with h5py.File(filename, 'r') as f:
                res=self.extract_dictionary(dict(), f['data'].attrs)
            return res
    
    def update_params(self, curve_id, **kwargs):
        if self.exists(curve_id):
            folder=self.get_folder_from_id(curve_id)
            filename=os.path.join(folder, '{:}.h5'.format(int(curve_id)))
            with h5py.File(filename, 'r+') as f:
                f['data'].attrs.update(kwargs)
    
    def remove_param(self, curve_id, key):
        if self.exists(curve_id):
            folder=self.get_folder_from_id(curve_id)
            filename=os.path.join(folder, '{:}.h5'.format(int(curve_id)))
            with h5py.File(filename, 'r+') as f:
                f['data'].attrs.pop(key)
    
    def get_childs(self, curve_id):
        if isinstance(curve_id, list):
            self.get_cursor()
            self.cursor.execute('''SELECT id, childs FROM data WHERE id=ANY(%s);''', (curve_id,))
            res = []
            for cid, childs in self.cursor.fetchall():
                res.append([int(cid), json.loads(childs)])
            return res
        elif self.exists(curve_id):
            self.get_cursor()
            self.cursor.execute('''SELECT childs FROM data WHERE id=%s;''', (int(curve_id),))
            res = self.cursor.fetchone()
            childs = json.loads(res[0])
            return childs
        else:
            return None
    
    
    def update_entry(self, curve):
        assert self.exists(curve.id)
        if len(curve.childs)>0:
            curve.childs=[int(i) for i in curve.childs]
        with transaction(self.db):
            self.get_cursor()
            self.cursor.execute('''UPDATE data SET name=%s, childs=%s, parent=%s, project=%s, sample=%s WHERE id=%s;''',
                                (curve.name, json.dumps(curve.childs),
                                 int(curve.parent), 
                                 curve.project,
                                 curve.sample,
                                 int(curve.id)))
    
    def delete_entry(self, curve_id):
        res=self.get_curve_metadata(curve_id)
        if res is not None:
            name, date, childs, parent, sample = res
            for child in childs:
                self.delete_entry(child)
            if parent!=int(curve_id):
                res=self.get_curve_metadata(parent)
                if res is not None:
                    name_parent, date_parent, childs_parent, parent_id, sample = res
                    if int(curve_id) in childs_parent:
                        childs_parent.remove(int(curve_id))
                        with transaction(self.db):
                            self.get_cursor()
                            self.cursor.execute('''UPDATE data SET childs=%s WHERE id=%s;''',
                                                (json.dumps(childs_parent),
                                                 int(parent)))
            directory=self.get_folder_from_date(date)
            filename=os.path.join(directory, '{:}.h5'.format(curve_id))
            if(os.path.exists(filename)):
                os.remove(filename)
            previous_dir=os.getcwd()
            if str(curve_id) in os.listdir(directory):
                os.chdir(directory)
                shutil.rmtree(str(curve_id))
            while((len(os.listdir(directory))==0)&(directory!=self.data_location)):
                os.rmdir(directory)
                directory=os.path.split(directory)[0]
            os.chdir(previous_dir)
            with transaction(self.db):
                self.get_cursor()
                self.cursor.execute('''DELETE FROM data WHERE id=%s;''',
                                    (int(curve_id),))
    
    def move(self, child, parent):
        if child != parent:
            res1, res2= (self.get_curve_childs_and_parent(child),
                         self.get_curve_childs_and_parent(parent))
            if res2 is not None and res1 is not None:
                childs_parent, parent_parent=res2
                childs_child, parent_child=res1
                childs_parent.append(child)
                if int(parent_child)!=child:
                    res3=self.get_curve_childs_and_parent(parent_child)
                    if res3 is not None:
                        childs_parent2, parent_parent2=res3
                        childs_parent2.remove(child)
                        with transaction(self.db):
                            self.get_cursor()
                            self.cursor.execute('''UPDATE data SET childs=%s WHERE id=%s;''',
                                                (json.dumps(childs_parent2),
                                                 int(parent_child)))
                with transaction(self.db):
                    self.get_cursor()
                    self.cursor.execute('''UPDATE data SET childs=%s WHERE id=%s;''',
                                        (json.dumps(childs_parent),
                                         int(parent)))
                    self.cursor.execute('''UPDATE data SET parent=%s WHERE id=%s;''',
                                        (json.dumps(parent),
                                         int(child)))
            
    
    def __del__(self):
        self.close()
    
    def exists(self, curve_id):
        self.get_cursor()
        self.cursor.execute('''SELECT id FROM data WHERE id=%s;''', (int(curve_id),))
        return self.cursor.fetchone() is not None
    
    def get_time_from_id(self, curve_id):
        if isinstance(curve_id, list):
            self.get_cursor()
            self.cursor.execute('''SELECT id, date FROM data WHERE id=ANY(%s);''',
                                (curve_id,))
            return self.cursor.fetchall()
        else:
            self.get_cursor()
            self.cursor.execute('''SELECT date FROM data WHERE id=%s;''',
                                (int(curve_id),))
            return float(self.cursor.fetchone()[0])

    def get_folder_from_date(self, date):
        path = os.path.join(self.data_location,
                            time.strftime("%Y",time.gmtime(date)),
                            time.strftime("%m",time.gmtime(date)),
                            time.strftime("%d",time.gmtime(date)))
        if not os.path.exists(path):
            os.makedirs(path)
        assert os.path.exists(path)
        return path
        
    def get_folder_from_id(self, curve_id):
        t = self.get_time_from_id(curve_id)
        path = os.path.join(self.data_location,
                            time.strftime("%Y",time.gmtime(t)),
                            time.strftime("%m",time.gmtime(t)),
                            time.strftime("%d",time.gmtime(t)))
        assert os.path.exists(path)
        return path
    
    def close(self):
        self.db.close()
        self.__class__.first_instance=True
        self.__class__.instances=[]

class Curve:

    def __init__(self, *args, **kwargs):
        if 'database' in kwargs.keys():
            self.database=kwargs.pop('database')
        else:
            self.database=SQLDatabase()
        if len(args)==0:
            self.x, self.y= np.array([]), np.array([])
            if 'name' in kwargs:
                self.name=kwargs.pop('name')
            else:
                self.name=""
            if 'project' in kwargs:
                self.project=kwargs.pop('project')
            else:
                self.project=""
            if 'sample' in kwargs:
                self.sample=kwargs.pop('sample')
            else:
                self.sample=""
            if 'comment' in kwargs:
                self.comment=kwargs.pop('comment')
            else:
                self.comment=""
            self.params = kwargs
            
            self.childs = list([])
            self.id=None
            self.parent=None
            if 'not_saved' not in kwargs.keys() or kwargs['not_saved'] is False:
                self.save() 
        elif len(args)==1 and np.isscalar(args[0]):
            self.copy(self.database.get_curve(args[0]))
        elif len(args)==3:
            self.id=args[0]
            for key in ['name', 'date', 'childs', 'parent', 'params', 'directory',
                        'project', 'sample']:
                assert key in kwargs.keys()
            self.name=kwargs.pop('name')
            self.date=kwargs.pop('date')
            self.childs=kwargs.pop('childs')
            self.parent=kwargs.pop('parent')
            self.params=kwargs.pop('params')
            if 'comment' in self.params.keys():
                self.comment=self.params.pop('comment')
            else:
                self.comment=""
            self.directory=kwargs.pop('directory')
            self.project=kwargs.pop('project')
            self.sample=kwargs.pop('sample')
            self.x=args[1]
            self.y=args[2]
        elif  len(args)==2 or len(args)==1 and not np.isscalar(args[0]):
            if len(args)==2:
                if len(args[0])!=len(args[1]):
                    raise(TypeError, "The format of the input is wrong")
                self.x = np.array(args[0])
                self.y = np.array(args[1])
            else:
                self.x = np.array(range(len(args[0])))
                self.y = np.array(args[0])
            if 'name' in kwargs:
                self.name=kwargs.pop('name')
            else:
                self.name=""
            if 'project' in kwargs:
                self.project=kwargs.pop('project')
            else:
                self.project=""
            if 'sample' in kwargs:
                self.sample=kwargs.pop('sample')
            else:
                self.sample=""
            if 'comment' in kwargs:
                self.comment=kwargs.pop('comment')
            else:
                self.comment=""
            self.params = kwargs
            self.childs = list([])
            self.id=None
            self.parent=None
            if 'not_saved' not in kwargs.keys() or kwargs['not_saved'] is False:
                self.save() 
        else:
            raise(TypeError, "The format of the input is wrong")
        
    def save(self):
        self.database.save(self)
        params=self.params.copy()
        params['comment']=self.comment
        with h5py.File(os.path.join(self.directory, '{:}.h5'.format(self.id)), 'w') as f:
            data=f.create_dataset('data', data=np.vstack((self.x, self.y)))
            for key, val in params.items():
                if val is None:
                    data.attrs[key]='NONE'
                elif isinstance(val, dict):
                    data.attrs[key]=json.dumps(val)
                else:
                    data.attrs[key]=val
                
    
    def remove_child(self, child_id):
        if int(child_id) in self.childs:
            child = self.database.get_curve(int(child_id))
            child.parent=child_id
            child.save()
            self.childs.remove(int(child_id))
        self.save()
    
    def set_name(self, name):
        self.name=name
        self.save()
        
    def has_parent(self):
        return self.id!=self.parent
    
    def move(self, curve_parent):
        assert curve_parent.id not in self.childs
        if self.parent!=self.id:
            parent=Curve(self.parent)
            try:
                parent.childs.remove(self.id)
                parent.save()
            except ValueError:
                pass
        self.parent = curve_parent.id
        curve_parent.childs.append(self.id)
        self.save()
        curve_parent.save()
        
    def exist_directory(self):
        return str(self.id) in os.listdir(self.directory)
    
    def copy(self, curve):
        self.id=curve.id
        self.x=curve.x
        self.y=curve.y
        self.name=curve.name
        self.project=curve.project
        self.sample=curve.sample
        self.params=curve.params
        self.date=curve.date
        self.childs=curve.childs
        self.parent=curve.parent
        self.database=curve.database
        self.directory=curve.directory
        self.comment=curve.comment
        
    def duplicate(self):
        curve=Curve(self.x, self.y, name=self.name, project=self.project, sample=self.sample, **self.params)
        print('id is {:}, name is {:}, project is {:}'.format(curve.id, curve.name, curve.project))
        childs=[]
        for child in self.childs:
            curve_child = Curve(child).duplicate()
            curve_child.parent=curve.id
            curve_child.save()
            childs.append(curve_child.id)
        curve.childs=childs
        curve.save()
        if str(self.id) in os.listdir(self.directory):
            shutil.copytree(os.path.join(self.directory, str(self.id)),
                            os.path.join(curve.directory, str(curve.id)))
        return curve
        
        
    def get_or_create_dir(self):

        if not str(self.id) in os.listdir(self.directory):
            os.mkdir(os.path.join(self.directory,str(self.id)))
        path = os.path.join(self.directory, str(self.id))
        assert os.path.exists(path)
        return path

    def delete(self):
        self.database.delete_entry(self.id)

class Test(QWidget):
    
    def __init__(self):
        super().__init__()
        
if __name__=='__main__':
    
    db=SQLDatabase()
    db.create_local_copy()



