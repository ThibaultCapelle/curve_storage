import os, json, time, shutil
from datetime import datetime
import numpy as np
import h5py
'''
class CURVE:

    def __init__(self, *args, **kwargs):
        self.id, self.folder = database.get_new_id()
        self.x, self.y = args
        self.params = kwargs

    def delete(self):
        database.delete(self.id)
'''

class DataBase:

    def __init__(self, database_location=None, data_location=r'C:\Users\Thibault\Documents\phd\python\Database_test'):
        if database_location is None:
            self.database_location = self.get_or_create_database()
        else:
            assert os.path.exists(database_location)
            self.database_location=database_location
        if not os.path.exists(data_location):
            os.makedirs(data_location)
        self.data_location=data_location

    def get_or_create_database(self):
        os.chdir(os.environ['HOMEPATH'])
        if not '.database' in os.listdir():
            os.mkdir('.database')
        os.chdir('.database')
        if 'database.json' in os.listdir():
            return os.path.join(os.getcwd(), 'database.json')
        else:
            with open('database.json', 'w') as f:
                json.dump(dict(), f)
            return os.path.join(os.getcwd(), 'database.json')
        
    def equalize_with_data(self):
        data = self.get_data()
        for k in data.keys():
            path = self.get_folder_from_id(k)
            if (not '{:}.h5'.format(k) in os.listdir(path)) or (not os.path.exists(path)):
                self.remove(k)

    def get_time_from_id(self, id):
        data = self.get_data()
        assert str(id) in data.keys()
        return data[str(id)]

    def get_folder_from_id(self, id):
        t = self.get_time_from_id(id)
        path = os.path.join(self.data_location,time.strftime("%Y\%m\%d",time.gmtime(t)))
        assert os.path.exists(path)
        return path

    def get_data(self):
        with open(self.database_location, 'r') as f:
            data=json.load(f)
        return data

    def get_last_id(self):
        data=self.get_data()
        result = 0
        for k in data.keys():
            if int(k)>result:
                result=int(k)
        return result
    
    def get_curve(self, curve_id):
        path = self.get_folder_from_id(curve_id)
        t = self.get_time_from_id(curve_id)
        assert '{:}.h5'.format(curve_id) in os.listdir(path)
        with h5py.File(os.path.join(path,'{:}.h5'.format(curve_id)), 'r') as f:
            data=f['data'].value
            params_stored = f['params']
            params=dict()
            for k,v in params_stored.items():
                params[k]=v.value
            childs = f['childs'].value
            parent = f['parent'].value
            name = f['name'].value
        curve = Curve(curve_id)
        if 'name' in params.keys():
            curve.name=params['name']
        else:
            curve.name=""
        curve.x=data[0]
        curve.y=data[1]
        curve.childs = childs
        curve.parent=parent
        curve.params=params
        curve.name=name
        return curve
            
    def new_id(self):
        new_id = self.get_last_id()+1
        new_time = time.time()
        with open(self.database_location, 'r') as f:
            data=json.load(f)
        data.update({new_id:new_time})
        with open(self.database_location, 'w') as f:
            json.dump(data, f)
        d = datetime.fromtimestamp(new_time)
        os.chdir(self.data_location)
        year = time.strftime("%Y",time.gmtime(new_time))
        month = time.strftime("%m",time.gmtime(new_time))
        day = time.strftime("%d",time.gmtime(new_time))
        if not year in os.listdir():
            os.mkdir(year)
        os.chdir(year)
        if not month in os.listdir():
            os.mkdir(month)
        os.chdir(month)
        if not day in os.listdir():
            os.mkdir(day)
        return new_id

    def remove(self, id):
        data = self.get_data()
        data.pop(str(id))
        with open(self.database_location, 'w') as f:
            json.dump(data, f)

class Curve:

    def __init__(self, *args, **kwargs):
        self.database = DataBase()
        if len(args)==1 and np.isscalar(args[0]):
            assert len(kwargs.keys())==0
            self.id=args[0]
            self.directory = self.database.get_folder_from_id(self.id)
            self.date = self.database.get_time_from_id(self.id)
        elif  len(args)==2:
            self.id=self.database.new_id()
            self.directory = self.database.get_folder_from_id(self.id)
            self.date = self.database.get_time_from_id(self.id)
            if len(args[0])!=len(args[1]):
                raise(TypeError, "The format of the input is wrong")
            self.x = np.array(args[0])
            self.y = np.array(args[1])
            if 'name' in kwargs:
                self.name=kwargs.pop('name')
            else:
                self.name=""
            self.params = kwargs
            self.childs = []
            self.parent = self.id
            self.save()
        else:
            raise(TypeError, "The format of the input is wrong")
        
    def save(self):
        with h5py.File(os.path.join(self.directory, '{:}.h5'.format(self.id)), 'w') as f:
            f.create_dataset('data', data=np.vstack((self.x, self.y)))
            params = f.create_group('params')
            for k, v in self.params.items():
                params[k]=v
            f.create_dataset('childs', data=self.childs)
            f.create_dataset('parent', data=self.parent)
            f.create_dataset('name', data=self.name)
    
    def move(self, curve_parent):
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
        self.database.remove(self.id)
        os.remove(os.path.join(self.directory, '{:}.h5'.format(self.id)))
        if self.exist_directory():
            os.chdir(self.directory)
            shutil.rmtree('/'+str(id))




