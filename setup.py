#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages 

setup(name='scrum_tool',
      version='0.0.1',
      description='A simple ncurses based scrum tool',
      author=['Josh Albert'],
      author_email=['albert@strw.leidenuniv.nl'],
    setup_requires=['npyscreen'],  
    tests_require=[
        'pytest>=2.8',
    ],
    package_dir = {'':'src'},
    packages=find_packages('src')
     )

