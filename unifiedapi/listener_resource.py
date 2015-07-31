# listener_resource.py - implements API for listener and notification resources
#
# Copyright 2015 Suomen Tilaajavastuu Oy
# All rights reserved.


'''Listener and notification resources in the HTTP API.'''


import time

import unifiedapi
import bottle


listener_prototype = {
    u'type': u'',
    u'id': u'',
    u'revision': u'',
    u'notify_of_new': False,
    u'listen_on': [u'']
}


notification_prototype = {
    u'type': u'',
    u'id': u'',
    u'listener_id': u'',
    u'revision': u'',
    u'resource_id': u'',
    u'resource_revision': u'',
    u'resource_change': u'',
    u'last_modified': 0
}


class ListenerResource(object):

    '''A listener (+ notification) resource in the HTTP API.

    A listener resource is one that stores listeners and notifications.
    Other resources such as /persons notify listener resource about changes.
    Notifications are added to the listeners that at the moment of change
    were listening to that specific type of change.

    This class is meant to be parameterised, not subclassed. Use the
    various set methods to set the parameters.

    The notify methods that other resources can call are:

    ``notify_create`` with arguments item id and new item revision

    ``notify_update`` with arguments item id and new item revision

    ``notify_delete`` with argument item id only

    '''

    def __init__(self):
        self._path = None
        self.database = None

    def set_top_resource_path(self, path):
        '''Set path of the top level resource, e.g., /persons.'''
        self._path = path

    def prepare_resource(self, database):
        '''Prepare the resource for action.'''

        self.database = database

        listeners_path = self._path + '/listeners'
        listener_paths = [
            {
                'path': listeners_path,
                'method': 'GET',
                'callback': self.get_listeners,
            },
            {
                'path': listeners_path,
                'method': 'POST',
                'callback': self.post_listener,
                'apply': unifiedapi.BasicValidationPlugin(),
            },
            {
                'path': listeners_path + '/<listener_id>',
                'method': 'GET',
                'callback': self.get_listener,
            },
            {
                'path': listeners_path + '/<listener_id>',
                'method': 'PUT',
                'callback': self.put_listener,
                'apply': unifiedapi.BasicValidationPlugin(u'listener_id'),
            },
            {
                'path': listeners_path + '/<listener_id>',
                'method': 'DELETE',
                'callback': self.delete_listener,
            }
        ]

        notifications_path = listeners_path + '/<listener_id>/notifications'
        notification_paths = [
            {
                'path': notifications_path,
                'method': 'GET',
                'callback': self.get_notifications,
            },
            {
                'path':
                notifications_path + '/<notification_id>',
                'method': 'GET',
                'callback':
                lambda listener_id, notification_id:
                self.get_notification(notification_id),
            },
            {
                'path':
                notifications_path + '/<notification_id>',
                'method': 'DELETE',
                'callback':
                lambda listener_id, notification_id:
                self.delete_notification(notification_id),
            }
        ]

        return listener_paths + notification_paths

    def get_listeners(self):
        '''Serve GET /foos/listeners to list all listeners.'''
        ro = self._create_resource_ro_storage(
            u'listener', listener_prototype)
        return {
            'resources': [
                {'id': resource_id} for resource_id in ro.get_item_ids()
            ],
        }

    def get_notifications(self, listener_id):
        '''Serve GET /foos/listeners/123/notifications.

        Lists all notifications.
        '''
        ro = self._create_resource_ro_storage(
            u'notification', notification_prototype)
        # Horribly inefficient start
        result = ro.search(
            [(u'exact', u'listener_id', listener_id)], [u'show_all'])
        result[u'resources'].sort(
            key=lambda resource: resource[u'last_modified'])
        result[u'resources'] = [
            {u'id': resource[u'id']} for resource in result[u'resources']
        ]
        # Horribly inefficient end
        return result

    def post_listener(self):
        '''Serve POST /foos/listeners to create a new listener.'''
        listener = bottle.request.json
        unifiedapi.add_missing_item_fields(
            u'listener', listener_prototype, listener)

        iv = unifiedapi.ItemValidator()
        try:
            iv.validate_item(u'listener', listener_prototype, listener)
        except unifiedapi.ValidationError as e:
            raise bottle.HTTPError(status=400)

        # Filling in default values sets the id field to None, if
        # missing. Thus we accept that and just remove it here.
        del listener[u'id']
        del listener[u'revision']

        wo = self._create_resource_wo_storage(
            u'listener', listener_prototype)
        return wo.add_item(listener)

    def get_listener(self, listener_id):
        '''Serve GET /foos/listeners/123 to get an existing listener.'''
        ro = self._create_resource_ro_storage(
            u'listener', listener_prototype)
        return ro.get_item(listener_id)

    def get_notification(self, notification_id):
        '''Serve GET /foos/listeners/123/notifications/123.

        Gets an existing notification.
        '''
        ro = self._create_resource_ro_storage(
            u'notification', notification_prototype)
        return ro.get_item(notification_id)

    def put_listener(self, listener_id):
        '''Serve PUT /foos/listeners/123 to update a listener.'''

        listener = bottle.request.json

        unifiedapi.add_missing_item_fields(
            u'listener', listener_prototype, listener)

        iv = unifiedapi.ItemValidator()
        try:
            iv.validate_item(u'listener', listener_prototype, listener)
            listener[u'id'] = listener_id
        except unifiedapi.ValidationError as e:
            raise bottle.HTTPError(status=400)

        try:
            wo = self._create_resource_wo_storage(
                u'listener', listener_prototype)
            updated = wo.update_item(listener)
        except unifiedapi.WrongRevision as e:
            raise bottle.HTTPError(status=409)

        return updated

    def delete_listener(self, listener_id):
        '''Serve DELETE /foos/listeners/123 to delete a listener.'''
        wo_listener = self._create_resource_wo_storage(
            u'listener', listener_prototype)
        wo_listener.delete_item(listener_id)

        ro = self._create_resource_ro_storage(
            u'notification', notification_prototype)
        notification_resources = ro.search(
            [(u'exact', u'listener_id', listener_id)], [])
        wo_notification = self._create_resource_wo_storage(
            u'notification', notification_prototype)
        for notification in notification_resources[u'resources']:
            try:
                wo_notification.delete_item(notification[u'id'])
            except unifiedapi.ItemDoesNotExist as e:
                # Try to delete all anyway
                pass

    def delete_notification(self, notification_id):
        '''Serve DELETE /foos/listeners/123/notifications/123.

        Deletes a notification.
        '''
        wo = self._create_resource_wo_storage(
            u'notification', notification_prototype)
        wo.delete_item(notification_id)

    def notify_create(self, item_id, item_revision):
        '''Adds a created notification.

        Notification is added for every listener that has notify_of_new
        enabled.
        '''
        ro = self._create_resource_ro_storage(
            u'listener', listener_prototype)
        listener_resources = ro.search(
            [(u'exact', u'notify_of_new', True)], [])

        wo = self._create_resource_wo_storage(
            u'notification', notification_prototype)
        for listener in listener_resources[u'resources']:
            notification = {
                u'type': u'notification',
                u'listener_id': listener[u'id'],
                u'resource_id': item_id,
                u'resource_revision': item_revision,
                u'resource_change': u'created',
                u'last_modified': int(time.time() * 1000000)
            }
            wo.add_item(notification)

    def notify_update(self, item_id, item_revision):
        '''Adds an updated notification.

        Notification is added for every listener that is listening on
        the updated item id.
        '''
        ro = self._create_resource_ro_storage(
            u'listener', listener_prototype)
        listener_resources = ro.search(
            [(u'exact', u'listen_on', item_id)], [])

        wo = self._create_resource_wo_storage(
            u'notification', notification_prototype)
        for listener in listener_resources[u'resources']:
            notification = {
                u'type': u'notification',
                u'listener_id': listener[u'id'],
                u'resource_id':  item_id,
                u'resource_revision': item_revision,
                u'resource_change': u'updated',
                u'last_modified': int(time.time() * 1000000)
            }
            wo.add_item(notification)

    def notify_delete(self, item_id):
        '''Adds an deleted notification.

        Notification is added for every listener that is listening on
        the updated item id.
        '''
        ro = self._create_resource_ro_storage(
            u'listener', listener_prototype)
        listener_resources = ro.search(
            [(u'exact', u'listen_on', item_id)], [])

        wo = self._create_resource_wo_storage(
            u'notification', notification_prototype)
        for listener in listener_resources[u'resources']:
            notification = {
                u'type': u'notification',
                u'listener_id': listener[u'id'],
                u'resource_id': item_id,
                u'resource_revision': None,
                u'resource_change': u'deleted',
                u'last_modified': int(time.time() * 1000000)
            }
            wo.add_item(notification)

    def _create_resource_ro_storage(self, resource_name, prototype):
        ro = unifiedapi.ReadOnlyStorage()
        ro.set_item_prototype(resource_name, prototype)
        ro.set_db(self.database)
        return ro

    def _create_resource_wo_storage(self, resource_name, prototype):
        wo = unifiedapi.WriteOnlyStorage()
        wo.set_item_prototype(resource_name, prototype)
        wo.set_db(self.database)
        return wo
