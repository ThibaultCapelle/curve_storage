# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 08:17:01 2020

@author: QMPL
"""

from curve_storage.database import Curve
import time
t_ini=time.time()
test_parent=Curve(name='test_parent')
curves=[]
for i in range(700):
    curves.append(Curve(name='test_child {:}'.format(i)))
print('creation of curves took {:}'.format(time.time()-t_ini))
t_ini=time.time()
for curve in curves:
    curve.move(test_parent)
print('moving of curves took {:}'.format(time.time()-t_ini))

    