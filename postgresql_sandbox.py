# -*- coding: utf-8 -*-
"""
Created on Fri Nov 20 17:27:51 2020

@author: Thibault
"""
import psycopg2

conn = psycopg2.connect(
    host="quarpi.qopt.nbi.dk",
    database="postgres",
    user="postgres")
