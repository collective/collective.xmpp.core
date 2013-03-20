from ZPublisher.pubevents import PubBeforeCommit
from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import IProductLayer
from collective.xmpp.core.interfaces import IXMPPSettings
from collective.xmpp.core.interfaces import IZopeReactor
from collective.xmpp.core.subscribers.startup import setUpAdminClient
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import applyProfile
from plone.registry.interfaces import IRegistry
from plone.testing import Layer
from twisted.internet.base import DelayedCall
from twisted.words.protocols.jabber.jid import JID
from zope.component import getUtility
from zope.component import queryUtility
from zope.configuration import xmlconfig
from zope.interface import alsoProvides
import time
import urllib2

DelayedCall.debug = True


def wait_on_deferred(d, seconds=10):
    for i in range(seconds*10):
        if d.called:
            return True
        time.sleep(0.1)
    else:
        assert False, 'Deferred never completed.'


def wait_on_client_deferreds(client, seconds=15):
    for i in range(seconds*10):
        if not client.xmlstream.iqDeferreds:
            return True
        time.sleep(0.1)
    else:
        assert False, 'Client deferreds never completed'


def wait_for_client_state(client, state, seconds=10):
    for i in range(seconds*10):
        if client.state == state:
            return True
        time.sleep(0.1)
    else:
        assert False, 'Client never reached state %s.' % state


def wait_for_reactor_state(reactor, state=True, seconds=20):
    for i in range(seconds*10):
        if reactor.running == state:
            return True
        time.sleep(0.1)
    else:
        assert False, 'Reactor never reached state %s.' % state


class FactoryWithJID(object):

    class Object(object):
        pass

    authenticator = Object()
    authenticator.jid = JID(u'user@example.com')


class EJabberdLayer(Layer):

    def setUp(self):
        # What follows is making sure we have ejabberd running and an
        # administrator account with JID admin@localhost and password 'admin'
        pm = urllib2.HTTPPasswordMgrWithDefaultRealm()
        url = 'http://localhost:5280/admin/'
        pm.add_password('ejabberd', url, 'admin@localhost', 'admin')
        handler = urllib2.HTTPBasicAuthHandler(pm)
        opener = urllib2.build_opener(handler)
        try:
            urllib2.install_opener(opener)
            urllib2.urlopen(url)
        except urllib2.URLError:
            print """
            You need to make available a running ejabberd server in order
            to run the functional tests, as well as give the user with JID
            admin@localhost and password 'admin' administrator privileges.
            Aborting tests...
            """
            exit(1)


EJABBERD_LAYER = EJabberdLayer()


class NoReactorFixture(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE, )

    def setUpZope(self, app, configurationContext):
        import collective.xmpp.core
        xmlconfig.file('configure.zcml', collective.xmpp.core,
                       context=configurationContext)

NO_REACTOR_FIXTURE = NoReactorFixture()

NO_REACTOR_INTEGRATION_TESTING = IntegrationTesting(
  bases=(NO_REACTOR_FIXTURE, ), name="NoReactorFixture:Integration")
NO_REACTOR_FUNCTIONAL_TESTING = FunctionalTesting(
  bases=(NO_REACTOR_FIXTURE, ), name="NoReactorFixture:Functional")


class ReactorFixture(PloneSandboxLayer):

    defaultBases = (EJABBERD_LAYER, NO_REACTOR_FIXTURE, )

    def setUpZope(self, app, configurationContext):
        import collective.xmpp.core
        xmlconfig.file('reactor.zcml', collective.xmpp.core,
                      context=configurationContext)
        zr = getUtility(IZopeReactor)
        zr.start()
        wait_for_reactor_state(zr.reactor, state=True)

    def testSetUp(self):
        zr = getUtility(IZopeReactor)
        zr.start()
        wait_for_reactor_state(zr.reactor, state=True)

    def testTearDown(self):
        # Clean ZopeReactor
        zr = getUtility(IZopeReactor)
        for dc in zr.reactor.getDelayedCalls():
            if not dc.cancelled:
                dc.cancel()
        zr.stop()
        wait_for_reactor_state(zr.reactor, state=False)
        #Clean normal reactor for the twisted unit tests.
        from twisted.internet import reactor
        reactor.disconnectAll()
        for dc in reactor.getDelayedCalls():
            if not dc.cancelled:
                dc.cancel()


REACTOR_FIXTURE = ReactorFixture()

REACTOR_INTEGRATION_TESTING = IntegrationTesting(
    bases=(REACTOR_FIXTURE, ), name="ReactorFixture:Integration")
REACTOR_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(REACTOR_FIXTURE, ), name="ReactorFixture:Functional")


class XMPPCoreNoReactorFixture(PloneSandboxLayer):

    defaultBases = (NO_REACTOR_FIXTURE, )

    def setUpZope(self, app, configurationContext):
        # Load ZCML
        import jarn.jsi18n
        import collective.xmpp.core
        xmlconfig.file('configure.zcml', jarn.jsi18n,
                       context=configurationContext)

        xmlconfig.file('configure.zcml', collective.xmpp.core,
                       context=configurationContext)

    def setUpPloneSite(self, portal):
        # Install into Plone site using portal_setup
        applyProfile(portal, 'collective.xmpp.core:default')
        registry = getUtility(IRegistry)
        registry['collective.xmpp.adminJID'] = 'admin@localhost'
        registry['collective.xmpp.pubsubJID'] = 'pubsub.localhost'
        registry['collective.xmpp.conferenceJID'] = 'conference.localhost'
        registry['collective.xmpp.xmppDomain'] = 'localhost'


XMPPCORE_NO_REACTOR_FIXTURE = XMPPCoreNoReactorFixture()

XMPPCORE_NO_REACTOR_INTEGRATION_TESTING = IntegrationTesting(
    bases=(XMPPCORE_NO_REACTOR_FIXTURE, ),
    name="XMPPCoreNoReactorFixture:Integration")
XMPPCORE_NO_REACTOR_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(XMPPCORE_NO_REACTOR_FIXTURE, ),
    name="XMPPCoreNoReactorFixture:Functional")


def _doNotUnregisterOnDisconnect(event):
    pass


class XMPPCoreFixture(PloneSandboxLayer):

    defaultBases = (REACTOR_FIXTURE, )

    def setUpZope(self, app, configurationContext):
        # Load ZCML
        import jarn.jsi18n
        import Products.UserAndGroupSelectionWidget
        import collective.xmpp.core
        xmlconfig.file('configure.zcml', jarn.jsi18n,
                       context=configurationContext)
        xmlconfig.file('configure.zcml', Products.UserAndGroupSelectionWidget,
                       context=configurationContext)

        # Normally on a client disconnect we unregister the AdminClient
        # utility. We can't do that here as we need to disconnect the
        # client and clean up to keep twisted happy.
        collective.xmpp.core.subscribers.startup.adminDisconnected = \
            _doNotUnregisterOnDisconnect

        xmlconfig.file('configure.zcml', collective.xmpp.core,
                       context=configurationContext)

    def setUpPloneSite(self, portal):
        # Install into Plone site using portal_setup
        applyProfile(portal, 'collective.xmpp.core:default')
        # Manually enable the browserlayer
        alsoProvides(portal.REQUEST, IProductLayer)

        # Start the reactor
        zr = getUtility(IZopeReactor)
        zr.start()
        wait_for_reactor_state(zr.reactor, state=True)

        registry = getUtility(IRegistry)
        settings = registry.forInterface(IXMPPSettings, check=False)
        settings.admin_jid = u'admin@localhost'
        settings.xmpp_domain = u'localhost'
        e = PubBeforeCommit(portal.REQUEST)
        setUpAdminClient(e)
        client = getUtility(IAdminClient)
        wait_for_client_state(client, u'authenticated')
        wait_on_client_deferreds(client)

    def tearDownPloneSite(self, portal):
        client = queryUtility(IAdminClient)
        if not client:
            # XXX: When running tests on runlevel 1, the IAdminClient is not
            # registered here.
            return
        zr = getUtility(IZopeReactor)
        zr.start()
        client.disconnect()
        wait_for_reactor_state(zr.reactor, state=True)
        wait_for_client_state(client, 'disconnected')
        zr.stop()


XMPPCORE_FIXTURE = XMPPCoreFixture()

XMPPCORE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(XMPPCORE_FIXTURE, ),
    name="XMPPCoreFixture:Integration")
XMPPCORE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(XMPPCORE_FIXTURE, ),
    name="XMPPCoreFixture:Functional")
