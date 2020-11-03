import os, json, time, shutil
import numpy as np
import h5py, sys
import sqlite3
import traceback

if not sys.platform=='linux':
    ROOT=os.environ['USERPROFILE']
else:
    ROOT=os.environ['HOME']


class SQLDatabase():
    
    first_instance = True
    instances = []
    highest_key = None
    CONFIG_LOCATION = ROOT
    assert 'database_config.json' in os.listdir(CONFIG_LOCATION)
    with open(os.path.join(CONFIG_LOCATION, 'database_config.json'), 'r') as f:
        res=json.load(f)
        DATA_LOCATION=res['DATA_LOCATION']
        DATABASE_LOCATION=res['DATABASE_LOCATION']
        DATABASE_NAME = res['DATABASE_NAME']
    
    def __init__(self, data_location=DATA_LOCATION):
        if not self.__class__.first_instance:
            self.db=self.__class__.instances[0]
            assert self.__class__.highest_key is not None
        else:
            self.__class__.first_instance=False
            if not '.database' in os.listdir(ROOT):
                os.mkdir(os.path.join(ROOT,'.database'))
            self.db=sqlite3.connect(os.path.join(SQLDatabase.DATABASE_LOCATION,
                                                 SQLDatabase.DATABASE_NAME))
            if not self.is_table_created():
                self.create_table()
            self.__class__.instances.append(self.db)
            self.__class__.highest_key=self.get_highest_key()
        self.data_location=data_location
        self.db=sqlite3.connect(os.path.join(SQLDatabase.DATABASE_LOCATION,
                                                 SQLDatabase.DATABASE_NAME))

    
    def get_all_ids(self):
        if self.is_table_created():
            self.get_cursor()
            self.cursor.execute('''SELECT id FROM data''')
            return np.array(self.cursor.fetchall()).flatten().tolist()
        else:
            return []
    
    def get_one_id(self):
        self.get_cursor()
        self.cursor.execute('''SELECT id FROM data''')
        return np.array(self.cursor.fetchone()).flatten()[0]
    
    def get_highest_key(self):
        self.get_cursor()
        self.cursor.execute('''SELECT id FROM data''')
        try:
            return np.array(self.cursor.fetchall()).max()
        except ValueError:
            return 0
    
    def get_all_hierarchy(self):
        self.get_cursor()
        self.cursor.execute('''SELECT id, childs, parent FROM data''')
        return self.cursor.fetchall()
    
    def get_name_and_time(self, curve_id):
        self.get_cursor()
        self.cursor.execute('''SELECT name, date FROM data WHERE id=?''', (int(curve_id),))
        return self.cursor.fetchone()
    
    def get_cursor(self):
        try:
            self.cursor=self.db.cursor()
        except sqlite3.ProgrammingError:
            self.db=sqlite3.connect(SQLDatabase.DATABASE_NAME)
            self.__class__.instances=[self.db]
            self.cursor=self.db.cursor()
    
    def get_n_keys(self):
        keys = self.get_all_ids()
        return len(keys)
        
    def is_table_created(self):
        self.get_cursor()
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return ('data',) in self.cursor.fetchall()
    
    def create_table(self):
        self.get_cursor()
        self.db.isolation_level='IMMEDIATE'
        try:
            self.cursor.execute('''
                           CREATE TABLE data(id INTEGER PRIMARY KEY, name TEXT,
                           date FLOAT, childs TEXT, parent INTEGER)
                           ''')
            self.db.commit()
        except sqlite3.Error as er:
            print('SQLite error: %s' % (' '.join(er.args)))
            print("Exception class is: ", er.__class__)
            print('SQLite traceback: ')
            exc_type, exc_value, exc_tb = sys.exc_info()
            print(traceback.format_exception(exc_type, exc_value, exc_tb))
        finally:
            self.db.isolation_level=None
        
    
    def save(self, curve):
        if curve.id is None:
            self.add_entry(curve)
        else:
            self.update_entry(curve)
        
    def add_entry(self, curve):
        assert curve.id is None
        curve_id = self.__class__.highest_key+1
        self.__class__.highest_key = curve_id
        curve.id=curve_id
        self.get_cursor()
        try:
            curve.date
        except AttributeError:
            curve.date=time.time()
        if curve.parent is None:
            curve.parent=curve.id
        self.db.isolation_level='IMMEDIATE'
        try:
            self.cursor.execute('''INSERT INTO data(id, name, date, childs, parent)
                      VALUES(?,?,?,?,?)''',
                      (int(curve_id),
                      curve.name,
                      float(curve.date),
                      json.dumps(curve.childs),
                      int(curve.parent)))
            self.db.commit()
        except sqlite3.Error as er:
            print('SQLite error: %s' % (' '.join(er.args)))
            print("Exception class is: ", er.__class__)
            print('SQLite traceback: ')
            exc_type, exc_value, exc_tb = sys.exc_info()
            print(traceback.format_exception(exc_type, exc_value, exc_tb))
            self.db.isolation_level=None
        curve.directory = self.get_folder_from_date(curve.date)
        curve.parent = curve_id
    
    def extract_dictionary(self, res, obj):
        for key, val in obj.items():
            if val=='NONE':
                res[key]=None
            elif isinstance(val, str) and val.startswith('{'):
                res[key]=json.loads(val)
            else:
                res[key]=val
        return res
    
    def get_curve(self, curve_id):
        assert self.exists(curve_id)
        self.get_cursor()
        self.cursor.execute('''SELECT name, date, childs, parent FROM data WHERE id=?''', (int(curve_id),))
        res = self.cursor.fetchone()
        name = res[0]
        date = float(res[1])
        childs = json.loads(res[2])
        parent = int(res[3])
        params = dict()
        directory=self.get_folder_from_date(date)
        if os.path.exists(os.path.join(directory, '{:}.h5'.format(curve_id))):
            with h5py.File(os.path.join(directory, '{:}.h5'.format(curve_id)), 'r') as f:
                data=f['data']
                x=data[0]
                y=data[1]
                params=self.extract_dictionary(params, data.attrs)
            return Curve(curve_id, x, y, database=self, name=name, date=date, childs=childs, parent=parent, params=params, directory=directory)
        else:
            return Curve(curve_id, [], [], database=self, name=name, date=date, childs=childs, parent=parent, params=params, directory=directory)

    def get_curve_metadata(self, curve_id):
        if self.exists(curve_id):
            self.get_cursor()
            self.cursor.execute('''SELECT name, date, childs, parent FROM data WHERE id=?''', (int(curve_id),))
            res = self.cursor.fetchone()
            name = res[0]
            date = float(res[1])
            childs = json.loads(res[2])
            parent = int(res[3])
            return name, date, childs, parent
        else:
            return None
    
    def get_params(self, curve_id):
        if self.exists(curve_id):
            folder=self.get_folder_from_id(curve_id)
            try:
                res=dict()
                with open(os.path.join(folder, '{:}.h5'), 'r') as f:
                    res=self.extract_dictionary(res, f['data'].attrs)
                return res
            except OSError:
                print('a data file could not be opened')
                return None
        else:
            return None
    
    def get_childs(self, curve_id):
        if self.exists(curve_id):
            self.get_cursor()
            self.cursor.execute('''SELECT childs FROM data WHERE id=?''', (int(curve_id),))
            res = self.cursor.fetchone()
            childs = json.loads(res[0])
            return childs
        else:
            return None
    
    
    def update_entry(self, curve):
        assert self.exists(curve.id)
        self.get_cursor()
        if len(curve.childs)>0:
            curve.childs=[int(i) for i in curve.childs]
        self.db.isolation_level='IMMEDIATE'
        try:
            self.cursor.execute('''UPDATE data SET name=?, childs=?, parent=? WHERE id=?''',
                                (curve.name, json.dumps(curve.childs),
                                 int(curve.parent), 
                                 int(curve.id)))
            self.db.commit()
        except sqlite3.Error as er:
            print('SQLite error: %s' % (' '.join(er.args)))
            print("Exception class is: ", er.__class__)
            print('SQLite traceback: ')
            exc_type, exc_value, exc_tb = sys.exc_info()
            print(traceback.format_exception(exc_type, exc_value, exc_tb))
        finally:
            self.db.isolation_level=None
    
    def delete_entry(self, curve_id):
        curve = self.get_curve(curve_id)
        for child in curve.childs:
            self.delete_entry(child)
        if curve.has_parent():
            parent = self.get_curve(curve.parent)
            parent.remove_child(curve_id)
        filename=os.path.join(curve.directory, '{:}.h5'.format(curve_id))
        if(os.path.exists(filename)):
            os.remove(filename)
        if curve.exist_directory():
            os.chdir(curve.directory)
            shutil.rmtree(str(curve_id))
        directory=curve.directory
        while((len(os.listdir(directory))==0)&(directory!=SQLDatabase.DATA_LOCATION)):
            os.rmdir(directory)
            directory=os.path.split(directory)[0]
        self.get_cursor()
        self.db.isolation_level='IMMEDIATE'
        try:
            self.cursor.execute('''DELETE FROM data WHERE id=?''',
                                (int(curve_id),))
            
            #curve.delete(delete_from_database=False)
            self.db.commit() 
        except sqlite3.Error as er:
            print('SQLite error: %s' % (' '.join(er.args)))
            print("Exception class is: ", er.__class__)
            print('SQLite traceback: ')
            exc_type, exc_value, exc_tb = sys.exc_info()
            print(traceback.format_exception(exc_type, exc_value, exc_tb))
        finally:
            self.db.isolation_level=None
    
    def __del__(self):
        self.close()
    
    def exists(self, curve_id):
        self.get_cursor()
        self.cursor.execute('''SELECT id FROM data WHERE id=?''', (int(curve_id),))
        return self.cursor.fetchone() is not None
    
    def get_time_from_id(self, curve_id):
        self.get_cursor()
        self.cursor.execute('''SELECT date FROM data WHERE id=?''', (int(curve_id),))
        return float(self.cursor.fetchone()[0])

    def get_folder_from_date(self, date):
        path = os.path.join(self.data_location,time.strftime("%Y/%m/%d",time.gmtime(date)))
        if not os.path.exists(path):
            os.makedirs(path)
        assert os.path.exists(path)
        return path
        
    def get_folder_from_id(self, id):
        t = self.get_time_from_id(id)
        path = os.path.join(self.data_location,time.strftime("%Y/%m/%d",time.gmtime(t)))
        assert os.path.exists(path)
        return path
    
    def delete_all_data(self):
        while(self.get_n_keys()>0):
            curve_id=self.get_one_id()
            self.delete_entry(curve_id)
    
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
            for key in ['name', 'date', 'childs', 'parent', 'params', 'directory']:
                assert key in kwargs.keys()
            self.name=kwargs.pop('name')
            self.date=kwargs.pop('date')
            self.childs=kwargs.pop('childs')
            self.parent=kwargs.pop('parent')
            self.params=kwargs.pop('params')
            self.directory=kwargs.pop('directory')
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
        with h5py.File(os.path.join(self.directory, '{:}.h5'.format(self.id)), 'w') as f:
            data=f.create_dataset('data', data=np.vstack((self.x, self.y)))
            for key, val in self.params.items():
                if val is None:
                    data.attrs[key]='NONE'
                elif isinstance(val, dict):
                    data.attrs[key]=json.dumps(val)
                else:
                    data.attrs[key]=val
                
    
    def remove_child(self, child_id):
        if child_id in self.childs:
            child = self.database.get_curve(child_id)
            child.parent=child_id
            self.childs.remove(child_id)
        self.save()
    
    def set_name(self, name):
        self.name=name
        self.save()
        
    def has_parent(self):
        return self.id!=self.parent
    
    def move(self, curve_parent):
        assert curve_parent.id not in self.childs
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
        self.params=curve.params
        self.date=curve.date
        self.childs=curve.childs
        self.parent=curve.parent
        self.database=curve.database
        self.directory=curve.directory
        self.directory=self.directory
        
    def get_or_create_dir(self):

        if not str(self.id) in os.listdir(self.directory):
            os.mkdir(os.path.join(self.directory,str(self.id)))
        path = os.path.join(self.directory, str(self.id))
        assert os.path.exists(path)
        return path

    def delete(self):
        self.database.delete_entry(self.id)

if __name__=='__main__':
    
    if sys.platform!='linux':
        os.chdir(os.environ['HOMEPATH'])
    else:
        os.chdir(os.environ['HOME'])
    if not '.database' in os.listdir():
        os.mkdir('.database')
    os.chdir('.database')
    database=SQLDatabase()
    curve=Curve([0,1,2,3], [1,2,3,4])
    curve.params['hello']='bonjour'
    curve.save()
    curve_id=curve.id
    retrieved_curve=database.get_curve(curve_id)
    retrieved_curve=database.get_curve(curve_id)
    retrieved_curve.delete()
    database.close()



