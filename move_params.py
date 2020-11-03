# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 08:17:01 2020

@author: QMPL
"""

from curve_storage.database import Curve, SQLDatabase
import sqlite3, json, h5py, os

db=SQLDatabase()
keys=db.get_all_ids()
'''
for key in keys:
    print(key)
    name, date, childs, parent=db.get_curve_metadata(key)
    params=db.get_params(key)
    directory=db.get_folder_from_date(date)
    try:
        with h5py.File(os.path.join(directory, '{:}.h5'.format(key)), 'r+') as f:
            data=f['data']
            for key, val in params.items():
                if val is None:
                    data.attrs[key]='NONE'
                elif isinstance(val, dict):
                    data.attrs[key]=json.dumps(val)
                else:
                    data.attrs[key]=val
    except OSError:
        print('a file was not found')'''
'''directory=db.get_folder_from_id(keys[0])
with h5py.File(os.path.join(directory, '{:}.h5'.format(keys[0])), 'r+') as f:
    data=f['data']
    for key, val in data.attrs.items():
        print(val)'''
curve=Curve(keys[0])
    


    

    