# -*- coding: utf-8 -*-
"""
Created on Mon Dec  6 11:01:35 2021

@author: Thibault
"""

from setuptools import setup

setup(name='curve_storage',
      version='1.0',
      packages=['curve_storage'],
      package_dir={
        'curve_storage': 'curve_storage',
      },
      install_requires=[
        'pyqtgraph<=0.11.0'
    ]
      )