# -*- coding: utf-8 -*-
"""
Created on Mon Dec  6 11:01:35 2021

@author: Thibault
"""

from setuptools import setup
import os
SETUP_PATH = os.path.dirname(os.path.abspath(__file__))

setup(name='curve_storage',
      version='1.0',
      packages=['curve_storage'],
      package_dir={
        'curve_storage': '.',
      },
      install_requires=[
        'pyqtgraph<=0.11.0'
    ]
      )