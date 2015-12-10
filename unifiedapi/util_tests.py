import unittest

import unifiedapi


class BasicRouteTests(unittest.TestCase):

    def test_basic_route_to_scope(self):
        route_scope = unifiedapi.route_to_scope('/orgs', 'GET')
        self.assertEqual(route_scope, u'uapi_orgs_get')

    def test_basic_id_route_to_scope(self):
        route_scope = unifiedapi.route_to_scope('/orgs/<item_id>', 'PUT')
        self.assertEqual(route_scope, u'uapi_orgs_id_put')

    def test_basic_subitem_route_to_scope(self):
        route_scope = unifiedapi.route_to_scope(
            '/orgs/<item_id>/document', 'PUT')
        self.assertEqual(route_scope, u'uapi_orgs_id_document_put')

    def test_search_route_to_scope(self):
        route_scope = unifiedapi.route_to_scope(
            '/orgs/search/<search_criteria:path>', 'GET')
        self.assertEqual(route_scope, u'uapi_orgs_search_id_get')

    def test_listener_notification_route_to_scope(self):
        route_scope = unifiedapi.route_to_scope(
            '/orgs/listeners/<id>/notifications/<id>', 'DELETE')
        self.assertEqual(
            route_scope, u'uapi_orgs_listeners_id_notifications_id_delete')


class TableNameTests(unittest.TestCase):

    def test_returns_correct_name_for_just_resource_type(self):
        name = unifiedapi.table_name(resource_type=u'foo')
        self.assertEqual(name, u'foo')

    def test_returns_name_for_list_field(self):
        name = unifiedapi.table_name(resource_type=u'foo', list_field=u'bar')
        self.assertEqual(name, u'foo_bar')

    def test_returns_name_for_string_list_in_dicts_in_dict_list(self):
        name = unifiedapi.table_name(
            resource_type=u'foo', list_field=u'bar', subdict_list_field=u'yo')
        self.assertEqual(name, u'foo_bar_yo')

    def test_returns_name_for_subresource(self):
        name = unifiedapi.table_name(
            resource_type=u'foo', subpath=u'bar')
        self.assertEqual(name, u'foo__path_bar')

    def test_returns_name_for_subresource_list_field(self):
        name = unifiedapi.table_name(
            resource_type=u'foo', subpath=u'bar', list_field=u'yo')
        self.assertEqual(name, u'foo__path_bar_yo')

    def test_returns_name_for_subresource_list_in_subdict(self):
        name = unifiedapi.table_name(
            resource_type=u'foo', subpath=u'bar', list_field=u'yo',
            subdict_list_field=u'ugh')
        self.assertEqual(name, u'foo__path_bar_yo_ugh')

    def test_returns_name_for_auxiliary_table(self):
        name = unifiedapi.table_name(
            resource_type=u'foo', auxtable=u'listeners')
        self.assertEqual(name, u'foo__aux_listeners')

    def test_returns_name_for_auxiliary_table_list_field(self):
        name = unifiedapi.table_name(
            resource_type=u'foo', auxtable=u'listeners', list_field=u'bar')
        self.assertEqual(name, u'foo__aux_listeners_bar')

    def test_fails_without_resource_type(self):
        with self.assertRaises(unifiedapi.ComplicatedTableNameError):
            unifiedapi.table_name()

    def test_fails_if_subdict_list_field_without_list_field(self):
        with self.assertRaises(unifiedapi.ComplicatedTableNameError):
            unifiedapi.table_name(
                resource_type=u'foo', subdict_list_field=u'bar')

    def test_fails_if_both_auxtable_and_subpath(self):
        with self.assertRaises(unifiedapi.ComplicatedTableNameError):
            unifiedapi.table_name(
                resource_type=u'foo', auxtable=u'aux', subpath=u'path')

    def test_fails_if_both_auxtable_and_subdict_list_field(self):
        with self.assertRaises(unifiedapi.ComplicatedTableNameError):
            unifiedapi.table_name(
                resource_type=u'foo', auxtable=u'aux',
                list_field='yo', subdict_list_field=u'bar')
