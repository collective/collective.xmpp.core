import unittest2 as unittest

from twisted.words.protocols.jabber.jid import JID

from collective.xmpp.core.component import XMPPComponent
from collective.xmpp.core.testing import REACTOR_INTEGRATION_TESTING
from collective.xmpp.core.testing import wait_for_client_state


class ComponentNetworkTest(unittest.TestCase):
    layer = REACTOR_INTEGRATION_TESTING
    level = 2

    def test_component_connection(self):
        """
        You'll need this in your ejabberd.cfg:

        {{5347, {0,0,0,0} }, ejabberd_service, []}
        """
        component = XMPPComponent('localhost',
                                  5347,
                                  'example.localhost',
                                  'secret')
        self.assertTrue(wait_for_client_state(component, 'authenticated'))
        self.assertEqual(component.jid, JID('example.localhost'))
