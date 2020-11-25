import os, json, time, shutil
import numpy as np
import h5py, sys
import psycopg2
from contextlib import contextmanager

if not sys.platform=='linux':
    ROOT=os.environ['USERPROFILE']
else:
    ROOT=os.environ['HOME']


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
        
class SQLDatabase():
    
    first_instance = True
    instances = []
    CONFIG_LOCATION = ROOT
    assert 'database_config.json' in os.listdir(CONFIG_LOCATION)
    with open(os.path.join(CONFIG_LOCATION, 'database_config.json'), 'r') as f:
        res=json.load(f)
        DATA_LOCATION=res['DATA_LOCATION']
        DATABASE_HOST=res['DATABASE_HOST']
        DATABASE_NAME = res['DATABASE_NAME']
        USER = res['USER']
    
    def __init__(self, data_location=DATA_LOCATION):
        if not self.__class__.first_instance:
            self.db=self.__class__.instances[0]
        else:
            self.__class__.first_instance=False
            self.db=psycopg2.connect(host=SQLDatabase.DATABASE_HOST,
                                     database=SQLDatabase.DATABASE_NAME,
                                     user=SQLDatabase.USER)
            if not self.is_table_created():
                self.create_table()
            self.__class__.instances.append(self.db)
        self.data_location=data_location

    
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
    
    def get_all_hierarchy(self, project=None):
        self.get_cursor()
        if project is None:
            self.cursor.execute('''SELECT id, childs, parent FROM data''')
        else:
            self.cursor.execute('''SELECT id, childs, parent FROM data WHERE project=%s''', (project,))
        return self.cursor.fetchall()
    
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
    
    def get_cursor(self):
        try:
            self.cursor=self.db.cursor()
        except psycopg2.InterfaceError:
            self.db=psycopg2.connect(host=SQLDatabase.DATABASE_HOST,
                                     database=SQLDatabase.DATABASE_NAME,
                                     user=SQLDatabase.USER)
            self.__class__.instances=[self.db]
            self.cursor=self.db.cursor()
    
    def get_n_keys(self):
        keys = self.get_all_ids()
        return len(keys)
        
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
                           date FLOAT, childs TEXT, parent INTEGER, project text);
                           ''')
        
    
    def save(self, curve):
        if curve.id is None:
            self.add_entry(curve)
        else:
            self.update_entry(curve)
        
    def add_entry(self, curve):
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
                self.cursor.execute('''INSERT INTO data(id, name, date, childs, parent, project)
                      VALUES(%s,%s,%s,%s,%s,%s);''',
                      (int(curve_id),
                      curve.name,
                      float(curve.date),
                      json.dumps(curve.childs),
                      int(curve.parent),
                      curve.project))
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
    
    
    def get_curve(self, *args):
        '''
        retrieve a curve. 
        -With a single scalar argument, return the Curve object with the id equal to this argument.
        -With a list of scalar argument, return a list of Curve objects with the ids equal to the list members
        -With a list of scalar as a first argument, and a string as a second argument, return the Curve object
        whose name matches the string and whose id belongs to the list
        '''
        if (len(args)>=1 and np.isscalar(args[0])):
            curve_id=args[0]
            if self.exists(curve_id):
                self.get_cursor()
                self.cursor.execute('''SELECT name, date, childs, parent, project FROM data WHERE id=%s;''', (int(curve_id),))
                res = self.cursor.fetchone()
                name = res[0]
                date = float(res[1])
                childs = json.loads(res[2])
                parent = int(res[3])
                params = dict()
                project = res[4]
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
                                 project=project)
                else:
                    return Curve(curve_id, [], [], database=self, name=name, 
                                 date=date, childs=childs, parent=parent, 
                                 params=params, directory=directory, project=project)
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
                self.cursor.execute('''SELECT id, name, date, childs, parent, project FROM data WHERE id=ANY(%s);''',(curve_ids,))
                res=[]
                for data in self.cursor.fetchall():
                    curve_id = int(data[0])
                    name = data[1]
                    date = float(data[2])
                    childs = json.loads(data[3])
                    parent = int(data[4])
                    params = dict()
                    project = data[5]
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
                                     project=project))
                    else:
                        res.append(Curve(curve_id, [], [], database=self, name=name, 
                                     date=date, childs=childs, parent=parent, 
                                     params=params, directory=directory, project=project))
                return res
        elif len(args)==2:
            if len(args[0])==1:
                return self.get_curve(args[0][0])
            else:
                curve_ids, name=args
                assert isinstance(curve_ids, list)
                assert isinstance(name, str)
                self.get_cursor()
                self.cursor.execute('''SELECT id, date, childs, parent, project FROM data WHERE id=ANY(%s) AND name=%s;''',
                                    (args[0], name))
                res=self.cursor.fetchone()
                if res is not None:
                    curve_id = int(res[0])
                    date = float(res[1])
                    childs = json.loads(res[2])
                    parent = int(res[3])
                    params = dict()
                    project = res[4]
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
                                     project=project)
                    else:
                        return Curve(curve_id, [], [], database=self, name=name, 
                                     date=date, childs=childs, parent=parent, 
                                     params=params, directory=directory, project=project)
                else:
                    print('no curve with this name was found')
                    return None
            
    def get_curve_metadata(self, curve_id):
        if self.exists(curve_id):
            self.get_cursor()
            self.cursor.execute('''SELECT name, date, childs, parent FROM data WHERE id=%s;''', (int(curve_id),))
            res = self.cursor.fetchone()
            name = res[0]
            date = float(res[1])
            childs = json.loads(res[2])
            parent = int(res[3])
            return name, date, childs, parent
        else:
            return None
    
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
            self.cursor.execute('''UPDATE data SET name=%s, childs=%s, parent=%s, project=%s WHERE id=%s;''',
                                (curve.name, json.dumps(curve.childs),
                                 int(curve.parent), 
                                 curve.project,
                                 int(curve.id) ))
    
    def delete_entry(self, curve_id):
        #curve = self.get_curve(curve_id)
        res=self.get_curve_metadata(curve_id)
        if res is not None:
            name, date, childs, parent = res
            for child in childs:
                self.delete_entry(child)
            if parent!=curve_id:
                res=self.get_curve_metadata(parent)
                if res is not None:
                    name_parent, date_parent, childs_parent, parent_id = res
                    childs_parent.remove(curve_id)
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
            while((len(os.listdir(directory))==0)&(directory!=SQLDatabase.DATA_LOCATION)):
                os.rmdir(directory)
                directory=os.path.split(directory)[0]
            os.chdir(previous_dir)
            with transaction(self.db):
                self.get_cursor()
                self.cursor.execute('''DELETE FROM data WHERE id=%s;''',
                                    (int(curve_id),))
    
    def move(self, child, parent):
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
                                    (json.dumps(parent_child),
                                     int(child)))
            
    
    def __del__(self):
        self.close()
    
    def exists(self, curve_id):
        self.get_cursor()
        self.cursor.execute('''SELECT id FROM data WHERE id=%s;''', (int(curve_id),))
        return self.cursor.fetchone() is not None
    
    def get_time_from_id(self, curve_id):
        self.get_cursor()
        self.cursor.execute('''SELECT date FROM data WHERE id=%s;''', (int(curve_id),))
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
            if 'project' in kwargs:
                self.project=kwargs.pop('project')
            else:
                self.project=""
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
                        'project']:
                assert key in kwargs.keys()
            self.name=kwargs.pop('name')
            self.date=kwargs.pop('date')
            self.childs=kwargs.pop('childs')
            self.parent=kwargs.pop('parent')
            self.params=kwargs.pop('params')
            self.directory=kwargs.pop('directory')
            self.project=kwargs.pop('project')
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
        self.params=curve.params
        self.date=curve.date
        self.childs=curve.childs
        self.parent=curve.parent
        self.database=curve.database
        self.directory=curve.directory
        
    def duplicate(self):
        curve=Curve(self.x, self.y, name=self.name, project=self.project, **self.params)
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

if __name__=='__main__':
    
    '''if sys.platform!='linux':
        os.chdir(os.environ['HOMEPATH'])
    else:
        os.chdir(os.environ['HOME'])
    if not '.database' in os.listdir():
        os.mkdir('.database')
    os.chdir('.database')'''
    database=SQLDatabase()
    '''curve=Curve([0,1,2,3], [1,2,3,4])
    curve.params['hello']='bonjour'
    curve.save()
    curve_id=curve.id
    retrieved_curve=database.get_curve(curve_id)
    retrieved_curve=database.get_curve(curve_id)
    retrieved_curve.delete()
    database.close()'''



