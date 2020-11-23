# -*- coding: utf-8 -*-
"""
Created on Fri Nov 20 17:27:51 2020

@author: Thibault
"""
import psycopg2, time

conn = psycopg2.connect(
    host="quarpi.qopt.nbi.dk",
    database="postgres",
    user="postgres")
cur=conn.cursor()

cur.execute('''INSERT INTO data(id, name, date, childs, parent, project)
                      VALUES(%s,%s,%s,%s,%s,%s);''', (1, "test", time.time(),
                      [], 1, 'test_project'))
conn.commit()
cur.close()
conn.close()

#%%
conn = psycopg2.connect(
    host="quarpi.qopt.nbi.dk",
    database="postgres",
    user="postgres")
cur=conn.cursor()
cur.execute('''SELECT id, name, date, childs, parent, project FROM data''')
res=cur.fetchall()
cur.close()
conn.close()

#%%
conn = psycopg2.connect(
    host="quarpi.qopt.nbi.dk",
    database="postgres",
    user="postgres")
cur=conn.cursor()
cur.execute('''SELECT max(id) FROM data''')
res=cur.fetchone()
cur.close()
conn.close()

#%%

from curve_storage.database import SQLDatabase, Curve

db=SQLDatabase()
curve=Curve([], [], name="test")
curve2=Curve([], [], name='test_child')
curve2.move(curve)
curve3=Curve([], [], name='test_grandchild')
curve3.move(curve2)
#%%
import psycopg2
conn = psycopg2.connect(
    host="quarpi.qopt.nbi.dk",
    database="postgres",
    user="postgres")
conn.rollback()
conn.close()
