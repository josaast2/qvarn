# simple_resource.py - a simple API resource
#
# Copyright 2015 Suomen Tilaajavastuu Oy
# All rights reserved.
import qvarn


class SimpleResource(object):

    '''Implement a simple resource such as /version.

    A simple resource can only ever be retrieved by GET. It can't be
    manipulated in any way.

    Parameterise this class with the ``set_path`` method.

    !IMPORTANT! Authorization to simple resources is not checked. They should
                only contain public information.

    '''

    def __init__(self):
        self._path = None
        self._callback = None

    def set_path(self, path, callback):
        self._path = path
        self._callback = callback

    def prepare_resource(self, database_url):
        return [
            {
                'path': self._path,
                'method': 'GET',
                'callback': self._callback,
                # Do not check authorization for simple resources
                'skip': [
                    qvarn.AuthorizationPlugin
                ]
            },
        ]