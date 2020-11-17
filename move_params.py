# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 08:17:01 2020

@author: QMPL
"""

from curve_storage.database import Curve

test_parent=Curve(name='test_parent')
for i in range(700):
    test_child=Curve(name='test_child {:}'.format(i))
    test_child.move(test_parent)

    