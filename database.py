import os, json, time, shutil
from datetime import datetime
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

    def get_folder_from_id(self, id):
        data = self.get_data()
        assert str(id) in data.keys()
        path = os.path.join(self.data_location,time.strftime("%Y\%M\%d",time.gmtime(data[str(id)])))
        assert os.path.exists(path)
        return path

    def get_data(self):
        with open(self.database_location, 'r') as f:
            data=json.load(f)
        return data

    def get_last_id(self):
        data=self.get_data()
        result = 1
        for k in data.keys():
            if int(k)>result:
                result=int(k)
        return result

    def new_id(self):
        new_id = self.get_last_id()+1
        new_time = time.time()
        with open(self.database_location, 'r') as f:
            data=json.load(f)
        data.update({new_id:new_time})
        with open(self.database_location, 'w') as f:
            json.load(data, f)
        d = datetime.fromtimestamp(new_time)
        os.chdir(self.data_location)
        if not str(d.year()) in os.listdir():
            os.mkdir(str(d.year()))
            os.chdir(str(d.year()))
        if not str(d.month()) in os.listdir():
            os.mkdir(str(d.month()))
            os.chdir(str(d.month()))
        if not str(d.day()) in os.listdir():
            os.mkdir(str(d.day()))
        return new_id

    def remove(self, id):
        data = self.get_data()
        data.pop(str(id))
        with open(self.database_location, 'w') as f:
            json.dump(data, f)

class Curve:

    def __init__(self, *args, **kwargs):
        self.database = DataBase()
        self.id=self.database.new_id()
        self.directory = self.database.get_folder_from_id(self.id)
        assert len(args)==2
        self.x, self.y = args
        self.params = kwargs

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
        if self.exist_directory():
            os.chdir(self.directory)
            shutil.rmtree('/'+str(id))




