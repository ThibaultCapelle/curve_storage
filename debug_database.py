# -*- coding: utf-8 -*-
"""
Created on Wed Nov 18 10:03:06 2020

@author: schli
"""

import sqlite3
import os, sys, json

if not sys.platform=='linux':
    ROOT=os.environ['USERPROFILE']
else:
    ROOT=os.environ['HOME']
    

CONFIG_LOCATION = ROOT
assert 'database_config.json' in os.listdir(CONFIG_LOCATION)
with open(os.path.join(CONFIG_LOCATION, 'database_config.json'), 'r') as f:
    res=json.load(f)
    DATA_LOCATION=res['DATA_LOCATION']
    DATABASE_LOCATION=res['DATABASE_LOCATION']
    DATABASE_NAME = res['DATABASE_NAME']
location=os.path.join(DATABASE_LOCATION, DATABASE_NAME)
db=sqlite3.connect(location)

db.execute('''pragma journal_mode=wal;''')
cursor=db.cursor()
cursor.execute('''CREATE TABLE data(id INTEGER PRIMARY KEY, name TEXT,
                           date FLOAT, childs TEXT, parent INTEGER, project text)
                           ''')
cursor=db.cursor()
cursor.execute('''SELECT id from data
                           ''')
res=cursor.fetchone()