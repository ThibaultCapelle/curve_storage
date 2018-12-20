# -*- coding: utf-8 -*-
"""
Created on Fri Dec 14 15:52:18 2018

@author: Thibault
"""
import os, h5py, time, json
import numpy as np
from curve_storage.database import DataBase, Curve
import matplotlib.pylab as plt
import sqlite3


path = r'C:\Users\Thibault\.database'
os.chdir(path)


N_s=np.logspace(1,6,20)#range(1, 1e6, 100)
time_writing=np.zeros(len(N_s))
time_reading=np.zeros(len(N_s))
time_reading_20_curves=np.zeros(len(N_s))
time_adding_one_curve=np.zeros(len(N_s))
file_size=np.zeros(len(N_s))
print("starting analyzing hdf5 performances...")

for i,N in enumerate(N_s):
    print('i:{:}, N:{:}'.format(i, N))
    if 'test.h5' in os.listdir():
        os.remove('test.h5')
    ids = range(int(N))
    t_ini = time.time()
    with h5py.File('test.h5','w') as f:
        for j in ids:
            if str(j) not in f.keys():
                f.create_group(str(j))
            f[str(j)]['name']="bonjour"
            f[str(j)]["date"]=time.time()
            f[str(j)].create_group("params")
            f[str(j)]['params']["string"]="hello"#.create_dataset("string", data="hello")
            f[str(j)]['params']["int"]=i#.create_dataset("int", data=i)
            f[str(j)]['params']["float"]=np.pi#.create_dataset("float", data=np.pi)
    time_writing[i]= time.time()-t_ini     
    file_size[i]=os.path.getsize('test.h5')
    #print("time for writing is {:.2f} s".format(time.time()-t_ini))   
    t_ini = time.time()
    with h5py.File('test.h5', 'a') as f:
        if str(j+1) not in f.keys():
            f.create_group(str(j+1))
        f[str(j+1)]['name']="bonjour"
        f[str(j+1)]["date"]=time.time()
        f[str(j+1)].create_group("params")
        f[str(j+1)]['params']["string"]="hello"#.create_dataset("string", data="hello")
        f[str(j+1)]['params']["int"]=i#.create_dataset("int", data=i)
        f[str(j+1)]['params']["float"]=np.pi#.create_dataset("float", data=np.pi)
    time_adding_one_curve[i]=time.time()-t_ini
    t_ini=time.time()
    with h5py.File('test.h5', 'r') as f:
        for j in ids:
            dset = f[str(j)]
            name = dset["name"].value
            date = dset["date"].value
            params = dict()
            params_dset = dset["params"]
            for key, value in params_dset.items():
                params[key]=value.value
    time_reading[i]= time.time()-t_ini
    if  len(ids)>20:
        t_ini=time.time()
        with h5py.File('test.h5', 'r') as f:
            for j in ids[len(ids)-20:]:
                dset = f[str(j)]
                name = dset["name"].value
                date = dset["date"].value
                params = dict()
                params_dset = dset["params"]
                for key, value in params_dset.items():
                    params[key]=value.value
        time_reading_20_curves[i]=time.time()-t_ini
    #print("time for reading is {:.2f} s".format(time.time()-t_ini)) 
np.save('time_reading.npy', time_reading)
np.save('time_writing.npy', time_writing)
np.save('time_adding_one_curve.npy', time_adding_one_curve)
np.save('time_reading_20_curves.npy', time_reading_20_curves)
np.save('file_size.npy', file_size)
plt.close("all")
plt.subplot(211)
plt.plot(N_s, time_reading, '.', label ='reading time')
plt.plot(N_s, time_writing, '.', label ='writing time')
plt.plot(N_s, time_adding_one_curve, '.', label ='adding one curve')
plt.plot(N_s, time_reading_20_curves, '.', label ='reading 20 curves')
plt.ylabel('time (s)')
plt.xlabel('number of curves') 
plt.title('hdf5 performance')
plt.legend()
plt.subplot(212)
plt.plot(N_s, file_size/1e3)
plt.xlabel('number of curves') 
plt.ylabel('size of the file (kB)')
plt.savefig('hdf5_performance.png') 

#%%
import os, h5py, time, json
import numpy as np
from curve_storage.database import DataBase, Curve
import matplotlib.pylab as plt
import sqlite3


path = r'C:\Users\Thibault\.database'
os.chdir(path)


N_s=np.logspace(1,6,20)#range(1, 1e6, 100)

time_writing_json=np.zeros(len(N_s))
time_reading_json=np.zeros(len(N_s))
time_reading_20_curves_json=np.zeros(len(N_s))
time_adding_one_curve_json=np.zeros(len(N_s))
file_size_json=np.zeros(len(N_s))

print("starting analyzing json performances...")

for i,N in enumerate(N_s):
    print('i:{:}, N:{:}'.format(i, N))
    if 'test.json' in os.listdir():
        os.remove('test.json')
    ids = range(int(N))
    t_ini = time.time()
    if not 'test.json' in os.listdir():
        with open('test.json', 'w') as f:
            json.dump(dict(),f)
    with open('test.json', 'r') as f:
        data = json.load(f)
    for j in ids:
        entry = dict()
        entry["name"]="bonjour"
        entry["date"]=time.time()
        entry["params"]=dict(string="hello",
                             int=i,
                             float=np.pi)
        data.update({j:entry})
    with open('test.json', 'w') as f:
        json.dump(data, f)
    time_writing_json[i]=time.time()-t_ini
    file_size_json[i]=os.path.getsize('test.json')
    t_ini = time.time()
    with open('test.json', 'r') as f:
        data=json.load(f)
    data[str(j+1)]=dict(name="bonjour",
         date=time.time(),
         params=dict(string="hello",
                     int=i,
                     float=np.pi))
    with open('test.json', 'w') as f:
        json.dump(data, f)
    time_adding_one_curve_json[i]=time.time()-t_ini
    t_ini = time.time()
    with open('test.json', 'r') as f:
        data=json.load(f)
    for j in ids:
        curve_data = data[str(j)]
        name = curve_data["name"]
        date = curve_data["date"]
        params = curve_data["params"]
        
    time_reading_json[i]=time.time()-t_ini
    if  len(ids)>20:
        t_ini=time.time()
        with open('test.json', 'r') as f:
            data=json.load(f)
        
        for j in ids[len(ids)-20:]:
            dset = data[str(j)]
            name = dset["name"]
            date = dset["date"]
            params = dset["params"]
        time_reading_20_curves_json[i]=time.time()-t_ini
    
np.save('time_reading_json.npy', time_reading_json)
np.save('time_writing_json.npy', time_writing_json)
np.save('time_adding_one_curve_json.npy', time_adding_one_curve_json)
np.save('time_reading_20_curves_json.npy', time_reading_20_curves_json)
np.save('file_size_json.npy', file_size_json)
plt.figure()
plt.subplot(211)
plt.plot(N_s, time_reading_json, '.', label ='reading time')
plt.plot(N_s, time_writing_json, '.', label ='writing time')
plt.plot(N_s, time_adding_one_curve_json, '.', label ='adding one curve')
plt.plot(N_s, time_reading_20_curves_json, '.', label ='reading 20 curves')
plt.ylabel('time (s)')
plt.xlabel('number of curves') 
plt.title('json performance')
plt.legend()
plt.subplot(212)
plt.plot(N_s, file_size_json/1e3)
plt.xlabel('number of curves') 
plt.ylabel('size of the file (kB)')
plt.savefig('json_performance.png') 

#%%
import os, h5py, time, json
import numpy as np
from curve_storage.database import DataBase, Curve
import matplotlib.pylab as plt
import sqlite3


path = r'C:\Users\Thibault\.database'
os.chdir(path)


N_s=np.logspace(1,6,20)#range(1, 1e6, 100)

time_writing_sql=np.zeros(len(N_s))
time_reading_sql=np.zeros(len(N_s))
time_reading_20_curves_sql=np.zeros(len(N_s))
time_adding_one_curve_sql=np.zeros(len(N_s))
file_size_sql=np.zeros(len(N_s))


class MyDatabase():
    
    def __init__(self):
        self.db=sqlite3.connect('database.db')
        self.cursor = self.db.cursor()
        self.cursor.execute('''
                       CREATE TABLE data(id INTEGER PRIMARY KEY, name TEXT,
                       date TEXT, params TEXT)
                       ''')
        self.db.commit()
    
    def add_entry(self, curve_id):
        if len(np.shape(curve_id))==0:
            self.cursor=self.db.cursor()
            self.cursor.execute('''INSERT INTO data(id, name, date, params)
                      VALUES(?,?,?,?)''', (int(curve_id), "bonjour", time.time(), json.dumps(dict(string="hello",
                                 int=int(curve_id),
                                 float=np.pi))))
            self.db.commit()
        elif len(np.shape(curve_id))==1:
            self.cursor=self.db.cursor()
            for c_id in curve_id:
                self.cursor.execute('''INSERT INTO data(id, name, date, params)
                      VALUES(?,?,?,?)''', (int(c_id), "bonjour", time.time(), json.dumps(dict(string="hello",
                                 int=int(c_id),
                                 float=np.pi))))
            self.db.commit()
        else:
            raise(TypeError, "The format of the input is wrong")
    
    def get_entry(self, curve_id):
        self.cursor=self.db.cursor()
        self.cursor.execute('''SELECT name, date, params FROM data WHERE id=?''', (curve_id,))
        curve = self.cursor.fetchone()
        name = curve[0]
        date = float(curve[1])
        params = json.loads(curve[2])

try:
    for i,N in enumerate(N_s):
        print('i:{:}, N:{:}'.format(i, N))
        if 'database' in locals():
            database.db.close()
        if 'database.db' in os.listdir():
            os.remove('database.db')
        ids = range(int(N))
        t_ini = time.time()
        database=MyDatabase()
        database.add_entry(ids)
        time_writing_sql[i]=time.time()-t_ini
        file_size_sql[i]=os.path.getsize('database.db')
        t_ini = time.time()
        database.add_entry(np.max(ids)+1)
        time_adding_one_curve_sql[i]=time.time()-t_ini
        t_ini = time.time()
        for j in ids:
            database.get_entry(j)
        time_reading_sql[i]=time.time()-t_ini
        if  len(ids)>20:
            t_ini=time.time()
            for j in ids[len(ids)-20:]:
                database.get_entry(j)
            time_reading_20_curves_sql[i]=time.time()-t_ini
        
finally:
    database.db.close()        
    np.save('time_reading_sql.npy', time_reading_sql)
    np.save('time_writing_sql.npy', time_writing_sql)
    np.save('time_adding_one_curve_sql.npy', time_adding_one_curve_sql)
    np.save('time_reading_20_curves_sql.npy', time_reading_20_curves_sql)
    np.save('file_size_sql.npy', file_size_sql)


plt.figure()
plt.subplot(211)
plt.plot(N_s, time_reading_sql, '.', label ='reading time')
plt.plot(N_s, time_writing_sql, '.', label ='writing time')
plt.plot(N_s, time_adding_one_curve_sql, '.', label ='adding one curve')
plt.plot(N_s, time_reading_20_curves_sql, '.', label ='reading 20 curves')
plt.ylabel('time (s)')
plt.xlabel('number of curves') 
plt.title('sql performance')
plt.legend()
plt.subplot(212)
plt.plot(N_s, file_size_sql/1e3)
plt.xlabel('number of curves') 
plt.ylabel('size of the file (kB)')
plt.savefig('sql_performance.png') 
   
#%%
import os, h5py, time, json
import numpy as np
from curve_storage.database import DataBase, Curve
import matplotlib.pylab as plt
import sqlite3


path = r'C:\Users\Thibault\.database'
os.chdir(path)


N_s=np.logspace(1,6,20)#range(1, 1e6, 100)
time_reading_json=np.load('time_reading_json.npy')
time_writing_json=np.load('time_writing_json.npy')
time_adding_one_curve_json=np.load('time_adding_one_curve_json.npy')
time_reading_20_curves_json=np.load('time_reading_20_curves_json.npy')
file_size_json=np.load('file_size_json.npy')

time_reading_sql=np.load('time_reading_sql.npy')
time_writing_sql=np.load('time_writing_sql.npy')
time_adding_one_curve_sql=np.load('time_adding_one_curve_sql.npy')
time_reading_20_curves_sql=np.load('time_reading_20_curves_sql.npy')
file_size_sql=np.load('file_size_sql.npy')

plt.figure(figsize=[20,10])
plt.subplot(321)
plt.plot(N_s, time_reading_json, '.', label ='reading time json')
plt.plot(N_s, time_reading_sql, '.', label ='reading time sql')
plt.ylabel('time (s)')
plt.xlabel('number of curves')
plt.legend()
plt.subplot(322)
plt.plot(N_s, time_writing_json, '.', label ='writing time json')
plt.plot(N_s, time_writing_sql, '.', label ='writing time sql')
plt.ylabel('time (s)')
plt.xlabel('number of curves')
plt.legend()
plt.subplot(323)
plt.plot(N_s, time_adding_one_curve_json, '.', label ='adding one curve json')
plt.plot(N_s, time_adding_one_curve_sql, '.', label ='adding one curve sql')
plt.ylabel('time (s)')
plt.xlabel('number of curves')
plt.legend()
plt.subplot(324)
plt.plot(N_s, time_reading_20_curves_json, '.', label ='reading 20 curves json')
plt.plot(N_s, time_reading_20_curves_sql, '.', label ='reading 20 curves sql')
plt.ylabel('time (s)')
plt.xlabel('number of curves')
plt.legend()
plt.legend()
plt.subplot(313)
plt.plot(N_s, file_size_sql/1e3, label='sql')
plt.plot(N_s, file_size_json/1e3, label='json')
plt.legend()
plt.xlabel('number of curves') 
plt.ylabel('size of the file (kB)')
plt.savefig('performance_comparizon_json_sql.png') 
    
