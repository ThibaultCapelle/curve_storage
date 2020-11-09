# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 08:17:01 2020

@author: QMPL
"""

from curve_storage.database import Curve, SQLDatabase
import sqlite3, json, h5py, os, sys

db=SQLDatabase()
db.get_cursor()
db.cursor.execute('''SELECT project FROM data WHERE id=?''', (1813,))
res=db.cursor.fetchall()
    


    

    