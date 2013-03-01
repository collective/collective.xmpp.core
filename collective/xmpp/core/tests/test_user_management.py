import unittest2 as unittest

from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from Products.CMFCore.utils import getToolByName
from zope.component import getUtility
from zope.interface import alsoProvides

from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import IProductLayer
from collective.xmpp.core.interfaces import IXMPPPasswordStorage
from collective.xmpp.core.testing import XMPPCORE_INTEGRATION_TESTING
from collective.xmpp.core.testing import wait_on_client_deferreds
from collective.xmpp.core.testing import wait_on_deferred
from collective.xmpp.core.utils import setup
# from collective.xmpp.core.utils.pubsub import getAllChildNodes


class UserManagementTests(unittest.TestCase):
    layer = XMPPCORE_INTEGRATION_TESTING
    level = 2

    def setUp(self):
        portal = self.layer['portal']
        alsoProvides(portal.REQUEST, IProductLayer)

    def test_add_delete_user(self):
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ['Manager'])
        client = getUtility(IAdminClient)

        mt = getToolByName(portal, 'portal_membership')
        mt.addMember('stpeter', 'secret', ['Member'], [])
        
        # Users aren't manually registered upon creation anymore, so lets do it
        # here.
        setup.registerXMPPUsers(portal, ['stpeter'])
        wait_on_client_deferreds(client)

        # User has been added
        d = client.admin.getRegisteredUsers()
        self.assertTrue(wait_on_deferred(d))
        result = d.result
        self.assertTrue(result.name, 'iq')
        self.assertTrue(result.attributes['type'], u'result')
        self.assertTrue(len(result.children), 1)
        self.assertTrue(result.children[0].name, u'query')
        self.assertTrue(result.children[0].attributes['node'], u'all users')
        self.assertTrue(len(result.children[0].children), 3)
        user_jids = [u.attributes[u'jid'] for u in result.children[0].children]
        self.assertTrue('stpeter@localhost' in user_jids)

        # TODO:
        # Check user's VCard

        # # User's pubsub node has been added
        # d = getAllChildNodes(client, 'people')
        # self.assertTrue(wait_on_deferred(d))
        # self.assertTrue('stpeter' in d.result['people'])

        pass_storage = getUtility(IXMPPPasswordStorage)
        self.assertTrue(pass_storage.get('stpeter') is not None)

        mt.deleteMembers('stpeter')
        wait_on_client_deferreds(client)
        # User has been deleted
        d = client.admin.getRegisteredUsers()
        wait_on_client_deferreds(client)

        result = d.result
        self.assertTrue(result.name, 'iq')
        self.assertTrue(result.attributes['type'], u'result')
        self.assertTrue(len(result.children), 1)
        self.assertTrue(result.children[0].name, u'query')
        self.assertTrue(result.children[0].attributes['node'], u'all users')
        self.assertTrue(len(result.children[0].children), 2)
        user_jids = [u.attributes[u'jid'] for u in result.children[0].children]
        self.assertTrue('stpeter@localhost' not in user_jids)
        self.assertTrue(pass_storage.get('stpeter') is None)

        # User's pubsub node has been removed
        # d = getAllChildNodes(client, 'people')
        # wait_on_client_deferreds(client)
        # self.assertTrue('stpeter' not in d.result['people'])
