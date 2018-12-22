import os, json, time, shutil
from datetime import datetime
import numpy as np
import h5py
import sqlite3




class SQLDatabase():
    
    first_instance = True
    instances = []
    highest_key = None
    DATA_LOCATION = r'C:\Users\Thibault\Documents\phd\python\Database_test'
    DATABASE_LOCATION = os.path.join(os.environ['HOMEPATH'], '.database')
    DATABASE_NAME = 'database.db'
    
    def __init__(self, data_location=DATA_LOCATION):
        if not self.__class__.first_instance:
            self.db=self.__class__.instances[0]
            assert self.__class__.highest_key is not None
        else:
            self.__class__.first_instance=False
            os.chdir(os.environ['HOMEPATH'])
            if not '.database' in os.listdir():
                os.mkdir('.database')
            os.chdir('.database')
            self.db=sqlite3.connect(SQLDatabase.DATABASE_NAME)
            if not self.is_table_created():
                self.create_table()
            self.__class__.instances.append(self.db)
            self.__class__.highest_key=self.get_highest_key()
        self.data_location=data_location
    
    def get_all_ids(self):
        self.get_cursor()
        self.cursor.execute('''SELECT id FROM data''')
        return np.array(self.cursor.fetchall()).flatten().tolist()
   
    def get_highest_key(self):
        self.get_cursor()
        self.cursor.execute('''SELECT id FROM data''')
        try:
            return np.array(self.cursor.fetchall()).max()
        except ValueError:
            return 0
        
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
        self.cursor.execute('''
                       CREATE TABLE data(id INTEGER PRIMARY KEY, name TEXT,
                       date FLOAT, childs TEXT, parent INTEGER, params TEXT)
                       ''')
        self.db.commit()
    
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
        self.cursor.execute('''INSERT INTO data(id, name, date, childs, parent, params)
                  VALUES(?,?,?,?,?,?)''',
                  (int(curve_id),
                  curve.name,
                  float(curve.date),
                  json.dumps(curve.childs),
                  int(curve.parent),
                  json.dumps(curve.params)))
        self.db.commit()
        curve.directory = self.get_folder_from_date(curve.date)
        curve.parent = curve_id
    
    def get_curve(self, curve_id):
        assert self.exists(curve_id)
        self.get_cursor()
        self.cursor.execute('''SELECT name, date, childs, parent, params FROM data WHERE id=?''', (int(curve_id),))
        res = self.cursor.fetchone()
        name = res[0]
        date = float(res[1])
        childs = json.loads(res[2])
        parent = int(res[3])
        params = json.loads(res[4])
        return Curve(curve_id, database=self, name=name, date=date, childs=childs, parent=parent, params=params)
    
    def get_curve_metadata(self, curve_id):
        assert self.exists(curve_id)
        self.get_cursor()
        self.cursor.execute('''SELECT name, date, childs, parent, params FROM data WHERE id=?''', (int(curve_id),))
        res = self.cursor.fetchone()
        name = res[0]
        date = float(res[1])
        childs = json.loads(res[2])
        parent = int(res[3])
        params = json.loads(res[4])
        return name, date, childs, parent, params
    
    def update_entry(self, curve):
        assert self.exists(curve.id)
        self.get_cursor()
        if len(curve.childs)>0:
            curve.childs=[int(i) for i in curve.childs]
        self.cursor.execute('''UPDATE data SET name=?, childs=?, parent=?, params=? WHERE id=?''',
                            (curve.name, json.dumps(curve.childs), int(curve.parent), json.dumps(curve.params), int(curve.id)))
        self.db.commit()
    
    def delete_entry(self, curve_id):
        curve = self.get_curve(curve_id)
        for child in curve.childs:
            self.delete_entry(child)
        if curve.has_parent():
            parent = self.get_curve(curve.parent)
            parent.remove_child(curve_id)
        self.get_cursor()
        self.cursor.execute('''DELETE FROM data WHERE id=?''',
                            (int(curve_id),))
        self.db.commit() 
    
    #def __del__(self):
    #    self.close()
    
    def exists(self, curve_id):
        self.get_cursor()
        self.cursor.execute('''SELECT id FROM data WHERE id=?''', (int(curve_id),))
        return self.cursor.fetchone() is not None
    
    def get_time_from_id(self, curve_id):
        self.get_cursor()
        self.cursor.execute('''SELECT date FROM data WHERE id=?''', (int(curve_id),))
        return float(self.cursor.fetchone()[0])

    def get_folder_from_date(self, date):
        path = os.path.join(self.data_location,time.strftime("%Y\%m\%d",time.gmtime(date)))
        if not os.path.exists(path):
            os.makedirs(path)
        assert os.path.exists(path)
        return path
        
    def get_folder_from_id(self, id):
        t = self.get_time_from_id(id)
        path = os.path.join(self.data_location,time.strftime("%Y\%m\%d",time.gmtime(t)))
        assert os.path.exists(path)
        return path
    
    def close(self):
        self.db.close()
        self.__class__.first_instance=True
        self.__class__.instances=[]
            

#class DataBase:
#
#    def __init__(self, database_location=None, data_location=r'C:\Users\Thibault\Documents\phd\python\Database_test'):
#        if database_location is None:
#            self.database_location = self.get_or_create_database()
#        else:
#            assert os.path.exists(database_location)
#            self.database_location=database_location
#        if not os.path.exists(data_location):
#            os.makedirs(data_location)
#        self.data_location=data_location
#
#    def get_or_create_database(self):
#        os.chdir(os.environ['HOMEPATH'])
#        if not '.database' in os.listdir():
#            os.mkdir('.database')
#        os.chdir('.database')
#        if DATABASE_NAME in os.listdir():
#            return os.path.join(os.getcwd(), DATABASE_NAME)
#        if 'database.json' in os.listdir():
#            return os.path.join(os.getcwd(), 'database.json')
#        else:
#            with open('database.json', 'w') as f:
#                json.dump(dict(), f)
#            return os.path.join(os.getcwd(), 'database.json')
#        
#    def equalize_with_data(self):
#        data = self.get_data()
#        for k in data.keys():
#            path = self.get_folder_from_id(k)
#            if (not '{:}.h5'.format(k) in os.listdir(path)) or (not os.path.exists(path)):
#                self.remove(k)
#
#    def get_time_from_id(self, id):
#        data = self.get_data()
#        assert str(id) in data.keys()
#        return data[str(id)]['time']
#
#    def get_folder_from_id(self, id):
#        t = self.get_time_from_id(id)
#        path = os.path.join(self.data_location,time.strftime("%Y\%m\%d",time.gmtime(t)))
#        assert os.path.exists(path)
#        return path
#
#    def get_data(self):
#        with open(self.database_location, 'r') as f:
#            data=json.load(f)
#        return data
#
#    def get_last_id(self):
#        data=self.get_data()
#        result = 0
#        for k in data.keys():
#            if int(k)>result:
#                result=int(k)
#        return result
#    
#    def get_whole_params_from_id(self, curve_id):
#        data = self.get_data()
#        assert str(curve_id) in data.keys()
#        return data[str(curve_id)]
#        
#    
#    def get_curve(self, curve_id):
#        path = self.get_folder_from_id(curve_id)
#        curve_params = self.get_whole_params_from_id(curve_id)
#        t = curve_params['time']
#        name = curve_params['name']
#        params = curve_params['params']
#        childs = curve_params['childs']
#        parent = curve_params['parent']
#        #t = self.get_time_from_id(curve_id)
#        assert '{:}.h5'.format(curve_id) in os.listdir(path)
#        with h5py.File(os.path.join(path,'{:}.h5'.format(curve_id)), 'r') as f:
#            data=f['data'].value

#           params_stored = f['params']
#            params=dict()
#            for k,v in params_stored.items():
#                params[k]=v.value
#            childs = list(f['childs'].value)
#            parent = f['parent'].value
#            name = f['name'].value
#
#        curve = Curve(curve_id)
#        #if 'name' in params.keys():
#        #    curve.name=params['name']
#        #else:
#        #    curve.name=""
#        curve.x=data[0]
#        curve.y=data[1]
#        curve.childs = childs
#        curve.parent=parent
#        curve.params=params
#        curve.name=name
#        curve.time=t
#        return curve
#            
#    def new_id(self):
#        new_id = self.get_last_id()+1
#        new_time = time.time()
#        with open(self.database_location, 'r') as f:
#            data=json.load(f)
#        curve_data = dict(time=new_time)
#        data.update({new_id:curve_data})
#        with open(self.database_location, 'w') as f:
#            json.dump(data, f)
#        d = datetime.fromtimestamp(new_time)
#        os.chdir(self.data_location)
#        year = time.strftime("%Y",time.gmtime(new_time))
#        month = time.strftime("%m",time.gmtime(new_time))
#        day = time.strftime("%d",time.gmtime(new_time))
#        if not year in os.listdir():
#            os.mkdir(year)
#        os.chdir(year)
#        if not month in os.listdir():
#            os.mkdir(month)
#        os.chdir(month)
#        if not day in os.listdir():
#            os.mkdir(day)
#        return new_id
#
#    def remove(self, id):
#        data = self.get_data()
#        data.pop(str(id))
#        with open(self.database_location, 'w') as f:
#            json.dump(data, f)
#            
        

class Curve:

    def __init__(self, *args, **kwargs):
        if 'database' in kwargs.keys():
            self.database=kwargs.pop('database')
        else:
            self.database=SQLDatabase()
        #self.database = DataBase()
        if len(args)==1 and np.isscalar(args[0]):
            self.id=args[0]
            self.name=kwargs.pop('name')
            self.date=kwargs.pop('date')
            self.childs=kwargs.pop('childs')
            self.parent=kwargs.pop('parent')
            self.params=kwargs.pop('params')
            self.directory=self.database.get_folder_from_date(self.date)
            if os.path.exists(os.path.join(self.directory, '{:}.h5'.format(self.id))):
                with h5py.File(os.path.join(self.directory, '{:}.h5'.format(self.id)), 'r') as f:
                    data=f['data']
                    self.x=data[0]
                    self.y=data[1]
        elif  len(args)==2:
            if len(args[0])!=len(args[1]):
                    raise(TypeError, "The format of the input is wrong")
            self.x = np.array(args[0])
            self.y = np.array(args[1])
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
            f.create_dataset('data', data=np.vstack((self.x, self.y)))
    
    def remove_child(self, child_id):
        assert child_id in self.childs
        self.childs.remove(child_id)
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

    def get_or_create_dir(self):
        os.chdir(self.directory)
        if not str(self.id) in os.listdir():
            os.mkdir(str(self.id))
        path = os.path.join(self.directory, str(self.id))
        assert os.path.exists(path)
        return path

    def delete(self):
        self.database.delete_entry(self.id)
        os.remove(os.path.join(self.directory, '{:}.h5'.format(self.id)))
        if self.exist_directory():
            os.chdir(self.directory)
            shutil.rmtree('/'+str(id))

if __name__=='__main__':
    
    os.chdir(os.environ['HOMEPATH'])
    if not '.database' in os.listdir():
        os.mkdir('.database')
    os.chdir('.database')
    if SQLDatabase.DATABASE_NAME in os.listdir():
        os.remove(SQLDatabase.DATABASE_NAME)
    database=SQLDatabase()
    curve=Curve([0,1,2,3], [1,2,3,4])
    curve.params['hello']='bonjour'
    curve.save()
    curve_id=curve.id
    retrieved_curve=database.get_curve(curve_id)
    retrieved_curve=database.get_curve(curve_id)
    retrieved_curve.delete()
    database.close()



