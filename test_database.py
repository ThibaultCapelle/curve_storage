# -*- coding: utf-8 -*-
"""
Created on Thu Dec  6 11:17:28 2018

@author: Thibault
"""

from curve_storage.database import Curve, SQLDatabase
import numpy as np
import os, shutil

database_path = os.path.join(os.environ['HOMEPATH'],'.database')
data_path = r'C:\Users\Thibault\Documents\phd\python\Database_test'

import unittest

class TestStringMethods(unittest.TestCase):

    def test_database_creation(self):
        database_fullpath = os.path.join(database_path, 'database.db')
        if os.path.exists(database_fullpath):
            SQLDatabase().delete_all_data()
            for file in os.listdir(data_path):
                shutil.rmtree(os.path.join(data_path, file), ignore_errors=True)
        curve = Curve([0,1,2,3], [0,2,2,2], name='bonjour')
        self.assertTrue(os.path.exists(database_fullpath))
        self.assertTrue(os.path.exists(curve.directory))
        self.assertEqual(len(os.listdir(curve.directory)),1)
        self.assertEqual(curve.id,1)
        self.assertEqual(curve.name,'bonjour')
        SQLDatabase().delete_all_data()
 
    def test_adding_curves(self):
        database_fullpath = os.path.join(database_path, 'database.db')
        if os.path.exists(database_fullpath):
            SQLDatabase().delete_all_data()
        curve = Curve([0,1,2,3], [0,2,2,2], name='bonjour')
        self.assertEqual(curve.database.get_n_keys(),1)
        self.assertEqual(curve.id,1)
        curve = Curve([0,1,2,3], [0,2,2,2], name='bonjour')
        self.assertEqual(curve.database.get_n_keys(),2)
        self.assertEqual(curve.id,2)
        SQLDatabase().delete_all_data()
  
    def test_retrieving_data(self):
        curve_1=Curve([0,1,2,3], [0,2,2,2], name='bonjour')
        curve_2=curve_1.database.get_curve(curve_1.id)
        self.assertEqual(curve_1.id, curve_2.id)
        self.assertEqual(curve_1.id, curve_1.parent)
        self.assertEqual(curve_1.name, curve_2.name)
        self.assertEqual(curve_1.date, curve_2.date)
        self.assertEqual(curve_1.parent, curve_2.parent)
        self.assertFalse((curve_1.x-curve_2.x).any())
        self.assertFalse((curve_1.y-curve_2.y).any())
        SQLDatabase().delete_all_data()
   
    def test_hierarchy(self):
        curve_1=Curve([0,1,2,3], [0,2,2,2], name='bonjour')
        self.assertEqual(curve_1.id, curve_1.parent)
        curve_2=Curve([0,1,2,3], [0,2,2,2], name='fiston')
        self.assertEqual(curve_2.id, curve_2.parent)
        curve_2.move(curve_1)
        self.assertEqual(curve_2.parent, curve_1.id)
        self.assertTrue(curve_2.id in curve_1.childs)
        SQLDatabase().delete_all_data()
    
    def test_parameter_modification(self):
        curve_1=Curve([0,1,2,3], [0,2,2,2], name='bonjour')
        size_1 = curve_1.database.get_n_keys()
        curve_1.params['foo']=25
        curve_1.save()
        size_2 = curve_1.database.get_n_keys()
        self.assertEqual(size_1, size_2)
        curve_2= curve_1.database.get_curve(curve_1.id)
        self.assertEqual(curve_2.params['foo'], 25)
        SQLDatabase().delete_all_data()
   
    def test_datashape_errors(self):
        with self.assertRaises(AssertionError):
            Curve([0,0],[1,1],[2,2])
        with self.assertRaises(TypeError):
            Curve([0,0,0],[1])
   
    def test_curve_directory(self):
        curve_1=Curve([0,1,2,3], [0,2,2,2])
        directory = curve_1.get_or_create_dir()
        self.assertTrue(os.path.exists(directory))
        self.assertTrue(curve_1.database.exists(curve_1.id))
        SQLDatabase().delete_all_data()

    def test_curve_removal(self):
        curve_1=Curve([0,1,2,3], [0,2,2,2])
        self.assertTrue(curve_1.database.exists(curve_1.id))
        curve_1.delete()
        self.assertTrue('{:}.h5'.format(curve_1.id) not in os.listdir(curve_1.directory))
        self.assertFalse(curve_1.database.exists(curve_1.id))
        SQLDatabase().delete_all_data()

if __name__ == '__main__':
    unittest.main()
