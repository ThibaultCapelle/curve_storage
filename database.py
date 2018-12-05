import os, json
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
        return data[str(id)]

    def 



