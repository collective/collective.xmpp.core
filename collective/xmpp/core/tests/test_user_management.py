import unittest2 as unittest
from ZPublisher.pubevents import PubBeforeCommit
from Products.CMFCore.utils import getToolByName
from zope.component import getUtility
from zope.component import getMultiAdapter
from zope.interface import alsoProvides
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import IProductLayer
from collective.xmpp.core.interfaces import IXMPPPasswordStorage
from collective.xmpp.core.testing import XMPPCORE_INTEGRATION_TESTING
from collective.xmpp.core.testing import wait_on_client_deferreds
from collective.xmpp.core.testing import wait_on_deferred
from collective.xmpp.core.testing import wait_for_client_state
from collective.xmpp.core.utils import setup
from collective.xmpp.core.subscribers.startup import setUpAdminClient


class UserManagementTests(unittest.TestCase):
    layer = XMPPCORE_INTEGRATION_TESTING
    level = 2

    def _addAndRegisterMembers(self, member_ids):
        portal = self.layer['portal']
        for mid in member_ids:
            self.mtool.addMember(mid, 'secret', ['Member'], [])
            # XXX: We have to do this separately, because the returned deferred is
            # only for the firt user (i.e we have no way of knowing when the
            # subsequent users have been registered.
            d = setup.registerXMPPUsers(portal, [mid])
            wait_on_client_deferreds(self.client)

    def _deleteMembers(self, member_ids):
        for mid in member_ids:
            self.mtool.deleteMembers([mid])
            wait_on_client_deferreds(self.client)

    def _checkRegistered(self, member_ids):
        pass_storage = getUtility(IXMPPPasswordStorage)
        d = self.client.admin.getRegisteredUsers()
        self.assertTrue(wait_on_deferred(d))
        result = d.result
        self.assertEqual(result.name, 'iq')
        self.assertEqual(result.attributes['type'], u'result')
        self.assertEqual(len(result.children), 1)
        self.assertEqual(result.children[0].name, u'query')
        self.assertEqual(result.children[0].attributes['node'], u'all users')
        for mid in member_ids:
            user_jids = [u.attributes[u'jid'] for u in result.children[0].children]
            self.assertTrue('%s@localhost' % mid in user_jids)
            self.assertTrue(pass_storage.get(mid) is not None)
            self.assertTrue(pass_storage.get(mid) is not None)

    def _checkDeregistered(self, member_ids):
        pass_storage = getUtility(IXMPPPasswordStorage)
        d = self.client.admin.getRegisteredUsers()
        wait_on_client_deferreds(self.client)
        result = d.result
        self.assertEqual(result.name, 'iq')
        self.assertEqual(result.attributes['type'], u'result')
        self.assertEqual(len(result.children), 1)
        self.assertEqual(result.children[0].name, u'query')
        self.assertEqual(result.children[0].attributes['node'], u'all users')
        user_jids = [u.attributes[u'jid'] for u in result.children[0].children]
        for mid in member_ids:
            self.assertTrue('%s@localhost' % mid not in user_jids)
            self.assertTrue(pass_storage.get(mid) is None)

    def setUp(self):
        portal = self.layer['portal']
        alsoProvides(portal.REQUEST, IProductLayer)
        setRoles(portal, TEST_USER_ID, ['Manager'])
        self.mtool = getToolByName(portal, 'portal_membership')
        # XXX: Necessary but not sure why, since it's already being
        # done in setUpPloneSite
        e = PubBeforeCommit(portal.REQUEST)
        setUpAdminClient(e)
        self.client = getUtility(IAdminClient)
        wait_for_client_state(self.client, u'authenticated')

    def test_add_delete_user(self):
        """ Create plone members and register them for XMPP.
            Then delete the plone members and check that their 
            XMPP counterparts are deregistered.
        """
        portal = self.layer['portal']
        member_ids = ['jmiller', 'stpeter']
        self._addAndRegisterMembers(member_ids)
        self._checkRegistered(member_ids)
        self._deleteMembers(member_ids)
        self._checkDeregistered(member_ids)

    def test_manual_deregistration(self):
        """ Create plone members and register them for XMPP.
            Then deregister them manually and check that all is fine.
        """
        portal = self.layer['portal']
        member_ids = ['jmiller', 'stpeter']
        self.client = getUtility(IAdminClient, context=portal)
        self._addAndRegisterMembers(member_ids)
        self._checkRegistered(member_ids)
        d = setup.deregisterXMPPUsers(portal, ['jmiller'])
        self.assertTrue(wait_on_deferred(d))
        self._checkDeregistered(['jmiller'])
        self._checkRegistered(['stpeter'])
        d = setup.deregisterXMPPUsers(portal, ['stpeter'])
        self.assertTrue(wait_on_deferred(d))
        self._checkDeregistered(['stpeter'])
