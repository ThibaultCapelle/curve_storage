# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 08:17:01 2020

@author: QMPL
"""

from curve_storage.database import SQLDatabase, transaction

db=SQLDatabase()

with transaction(db.db):
    db.get_cursor()
    db.cursor.execute('''SELECT id, project FROM data WHERE project=%s''', ('Electromechanics',))
    res=db.cursor.fetchall()
    
    