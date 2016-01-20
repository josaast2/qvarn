#!/usr/bin/python
#
# setup.py - standard Python build-and-package program
#
# Copyright 2015 Suomen Tilaajavastuu Oy
# All rights reserved.


from distutils.core import setup


setup(
    name='qvarn',
    version='0.1',
    description='backend service for JSON and binary data storage',
    author='Suomen Tilaajavastuu Oy',
    author_email='tilaajavastuu.hifi@tilaajavastuu.fi',
    packages=['qvarn'],
)
