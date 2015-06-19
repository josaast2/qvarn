# list_resource.py - implement API for multi-item resources such as /persons
#
# Copyright 2015 Suomen Tilaajavastuu Oy
# All rights reserved.


'''Multi-item resources in the HTTP API.'''


import logging

import unifiedapi
import unifiedapi.bottle as bottle


class ListResource(object):

    '''A multi-item resource in the HTTP API.

    A multi-item resource is one such as /persons, where the top level
    resource has any number of sub-resources, one per person, and the
    API client can access and manage the sub-items individually.

    This class is meant to be parameterised, not subclassed. Use the
    various set methods to set the parameters.

    '''

    def __init__(self):
        self._path = None
        self._item_type = None
        self._item_prototype = None
        self._item_validator = None
        self._subitem_prototypes = unifiedapi.SubItemPrototypes()
        self._preparer = None
        self.database = None

    def set_path(self, path):
        '''Set path of the top level resource, e.g., /persons.'''
        self._path = path

    def set_item_type(self, item_type):
        '''Set the type of items, e.g., u'person'.'''
        self._item_type = item_type

    def set_item_prototype(self, item_prototype):
        '''Set the prototype for each sub-item.'''
        self._item_prototype = item_prototype

    def set_item_validator(self, item_validator):
        '''Set function to provide item-specific validation.

        Note that ``item_validator`` does not need to do generic
        validation against the prototype, as that is handled
        automatically.

        '''

        self._item_validator = item_validator

    def set_subitem_prototype(self, subitem_name, prototype):
        '''Set prototype for a subitem.'''
        self._subitem_prototypes.add(self._item_type, subitem_name, prototype)

    def set_storage_preparer(self, preparer):
        '''Set the storage preparer.'''
        self._preparer = preparer

    def prepare_resource(self, database_url):
        '''Prepare the resource for action.'''

        self.database = database_url

        # Make sure the database exists.
        self._create_wo_storage()

        item_paths = [
            {
                'path': self._path,
                'method': 'GET',
                'callback': self.get_items,
            },
            {
                'path': self._path,
                'method': 'POST',
                'callback': self.post_item,
            },
            {
                'path': self._path + '/<item_id>',
                'method': 'GET',
                'callback': self.get_item,
            },
            {
                'path': self._path + '/<item_id>',
                'method': 'PUT',
                'callback': self.put_item,
            },
            {
                'path': self._path + '/<item_id>',
                'method': 'DELETE',
                'callback': self.delete_item,
            },
            {
                'path': self._path + '/search/<search_criteria:path>',
                'method': 'GET',
                'callback': self.get_matching_items,
            },
        ]

        subitem_paths = []
        for subitem_name, _ in self._subitem_prototypes.get_all():
            subitem_path = self._path + '/<item_id>/' + subitem_name
            subitem_paths.extend([
                {
                    'path': subitem_path,
                    'method': 'GET',
                    'callback':
                    lambda item_id, x=subitem_name:
                    self.get_subitem(item_id, x),
                },
                {
                    'path': subitem_path,
                    'method': 'PUT',
                    'callback':
                    lambda item_id, x=subitem_name:
                    self.put_subitem(item_id, x),
                }
            ])

        return item_paths + subitem_paths

    def get_items(self):
        '''Serve GET /foos to list all items.'''
        unifiedapi.log_request()
        ro = self._create_ro_storage()
        return {
            'resources': [
                {'id': resource_id} for resource_id in ro.get_item_ids()
            ],
        }

    def get_matching_items(self, search_criteria):
        '''Serve GET /foos/search to list items matching search criteria.'''
        unifiedapi.log_request()
        ro = self._create_ro_storage()

        criteria = search_criteria.split('/')
        search_params = []
        show_params = []

        for i in range(len(criteria)):
            if i % 3 == 0:
                if criteria[i] in [u'exact']:
                    matching_rule = criteria[i]
                elif criteria[i] == u'show_all':
                    show_params.append(criteria[i])
                    break
                else:
                    raise bottle.HTTPError(status=400)
            elif i % 3 == 1:
                search_field = criteria[i]
            elif i % 3 == 2:
                search_value = criteria[i]
                search_param = (matching_rule, search_field, search_value)
                search_params.append(search_param)

        return ro.search(search_params, show_params)

    def post_item(self):
        '''Serve POST /foos to create a new item.'''
        unifiedapi.log_request()
        item = bottle.request.json
        unifiedapi.add_missing_item_fields(
            self._item_type, self._item_prototype, item)

        iv = unifiedapi.ItemValidator()
        try:
            iv.validate_item(self._item_type, self._item_prototype, item)
            self._validate_no_id_given(item)
            self._validate_no_revision_given(item)
            self._item_validator(item)
        except unifiedapi.ValidationError as e:
            logging.error(u'Validation error: %s', e)
            raise bottle.HTTPError(status=400)

        wo = self._create_wo_storage()
        return wo.add_item(item)

    def _validate_no_id_given(self, item):
        if u'id' in item:
            if item[u'id'] is not None:
                raise NewItemHasIdAlready(id=item[u'id'])

            # Filling in default values sets the id field to None, if
            # missing. Thus we accept that and just remove it here.
            del item[u'id']

    def _validate_no_revision_given(self, item):
        if u'revision' in item:
            if item[u'revision'] is not None:
                raise NewItemHasRevisionAlready(revision=item[u'revision'])

            # Filling in default values sets the revision field to None, if
            # missing. Thus we accept that and just remove it here.
            del item[u'revision']

    def get_item(self, item_id):
        '''Serve GET /foos/123 to get an existing item.'''
        unifiedapi.log_request()
        ro = self._create_ro_storage()
        item_id = self._get_path_arg_as_unicode(item_id)
        try:
            return ro.get_item(item_id)
        except unifiedapi.ItemDoesNotExist as e:
            logging.error(str(e), exc_info=True)
            raise bottle.HTTPError(status=404)

    def _get_path_arg_as_unicode(self, item_id):
        # bottle.py gives as args from paths as str, we need them as unicode.
        return unicode(item_id)

    def get_subitem(self, item_id, subitem_path):
        '''Serve GET /foos/123/subitem.'''
        unifiedapi.log_request()
        ro = self._create_ro_storage()
        item_id = self._get_path_arg_as_unicode(item_id)
        try:
            subitem = ro.get_subitem(item_id, subitem_path)
        except unifiedapi.ItemDoesNotExist as e:
            logging.error(str(e), exc_info=True)
            raise bottle.HTTPError(status=404)

        item = ro.get_item(item_id)
        subitem[u'revision'] = item[u'revision']
        return subitem

    def put_item(self, item_id):
        '''Serve PUT /foos/123 to update an item.'''
        unifiedapi.log_request()

        item_id = self._get_path_arg_as_unicode(item_id)
        item = bottle.request.json

        unifiedapi.add_missing_item_fields(
            self._item_type, self._item_prototype, item)

        iv = unifiedapi.ItemValidator()
        try:
            iv.validate_item(self._item_type, self._item_prototype, item)
            self._validate_id_is_valid_if_given(item, item_id)
            item[u'id'] = item_id
            self._item_validator(item)
        except unifiedapi.ValidationError as e:
            logging.error(u'Validation error: %s', e)
            raise bottle.HTTPError(status=400)

        try:
            wo = self._create_wo_storage()
            updated = wo.update_item(item)
        except unifiedapi.WrongRevision as e:
            logging.error(u'Validation error: %s', e)
            raise bottle.HTTPError(status=409)

        return updated

    def _validate_id_is_valid_if_given(self, item, item_id):
        if item[u'id'] not in (None, item_id):
            raise ItemHasConflictingId(id=item[u'id'], wanted=item_id)

    def put_subitem(self, item_id, subitem_name):
        '''Serve PUT /foos/123/subitem to update a subitem.'''
        unifiedapi.log_request()

        item_id = self._get_path_arg_as_unicode(item_id)
        subitem = bottle.request.json

        subitem_type = u'%s_%s' % (self._item_type, subitem_name)
        prototype = self._subitem_prototypes.get(self._item_type, subitem_name)
        unifiedapi.add_missing_item_fields(subitem_type, prototype, subitem)

        iv = unifiedapi.ItemValidator()
        try:
            if u'revision' not in subitem:
                raise NoSubitemRevision(id=item_id)
            revision = subitem.pop(u'revision')
            iv.validate_item(subitem_type, prototype, subitem)
        except NoSubitemRevision as e:
            logging.error(u'Validation error: %s', e)
            raise bottle.HTTPError(status=409)
        except unifiedapi.ValidationError as e:
            logging.error(u'Validation error: %s', e)
            raise bottle.HTTPError(status=400)

        try:
            wo = self._create_wo_storage()
            subitem[u'revision'] = wo.update_subitem(
                item_id, revision, subitem_name, subitem)
        except unifiedapi.WrongRevision as e:
            logging.error(u'Validation error: %s', e)
            raise bottle.HTTPError(status=409)
        return subitem

    def delete_item(self, item_id):
        '''Serve DELETE /foos/123 to delete an item.'''
        unifiedapi.log_request()
        wo = self._create_wo_storage()
        item_id = self._get_path_arg_as_unicode(item_id)
        try:
            wo.delete_item(item_id)
        except unifiedapi.ItemDoesNotExist as e:
            logging.error(str(e), exc_info=True)
            raise bottle.HTTPError(status=404)

    def _create_ro_storage(self):
        ro = unifiedapi.ReadOnlyStorage()
        ro.set_item_prototype(self._item_type, self._item_prototype)
        for subitem_name, prototype in self._subitem_prototypes.get_all():
            ro.set_subitem_prototype(self._item_type, subitem_name, prototype)
        db = unifiedapi.open_disk_database(self.database)
        ro.set_db(db)
        return ro

    def _create_wo_storage(self):
        wo = unifiedapi.WriteOnlyStorage()
        wo.set_item_prototype(self._item_type, self._item_prototype)
        for subitem_name, prototype in self._subitem_prototypes.get_all():
            wo.set_subitem_prototype(self._item_type, subitem_name, prototype)
        wo.set_preparer(self._preparer)

        db = unifiedapi.open_disk_database(self.database)
        wo.set_db(db)
        wo.prepare()

        return wo


class NewItemHasIdAlready(unifiedapi.ValidationError):

    msg = u'New item has id already set ({id!r}), which is not allowed'


class NewItemHasRevisionAlready(unifiedapi.ValidationError):

    msg = (
        u'New item has revision already set ({revision!r}), '
        u'which is not allowed')


class ItemHasConflictingId(unifiedapi.ValidationError):

    msg = u'Updated item {wanted} has conflicting id {id}'


class NoSubitemRevision(unifiedapi.ValidationError):

    msg = u'Sub-item for {id} has no revision'
