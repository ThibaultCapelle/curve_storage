import os, json, time
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

class database:

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
        with open(self.database_location, 'r') as f:
            data=json.load(f)
        assert str(id) in data.keys()
        path = time.strftime("%Y\%M\%d",time.gmtime(data[str(id)]))
        return os.path.join(self.data_location,path)

    def get_last_id(self):
        with open(self.database_location, 'r') as f:
            data=json.load(f)
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





