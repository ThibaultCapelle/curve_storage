# -*- coding: utf-8 -*-
"""
Created on Wed Nov 18 10:03:06 2020

@author: schli
"""

from curve_storage.database import SQLDatabase, Curve
db=SQLDatabase()

db.get_cursor()
db.cursor.execute('''PRAGMA mmap_size;''')
res=db.cursor.fetchall()
