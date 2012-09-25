import logging

from plone.registry.interfaces import IRegistry
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite

from Products.CMFCore.utils import getToolByName

from jarn.xmpp.twisted.interfaces import IZopeReactor

from collective.xmpp.core.client import AdminClient
from collective.xmpp.core.interfaces import IAdminClient

log = logging.getLogger(__name__)

def setUpAdminClient(event):
    if "plone_javascript_variables.js" not in event.request.steps:
        # XXX: This is a bit of a hack to make sure that we don't register the
        # utility a zillion times (which can cause runtime errors).
        # This package in any case depends on the above file being present, so
        # we check if it's being loaded.
        # A more elegant solution would be welcome :)
        return
    site = getSite()
    mtool = getToolByName(site, 'portal_membership')
    if mtool.isAnonymousUser():
        return
    client = queryUtility(IAdminClient)
    if client is None:
        settings = getUtility(IRegistry)
        try:
            jid = settings['collective.xmpp.adminJID']
            jdomain = settings['collective.xmpp.xmppDomain']
            password = settings['collective.xmpp.adminPassword']
        except KeyError:
            return

        client = AdminClient(jid, jdomain, password)
        gsm = getGlobalSiteManager()
        gsm.registerUtility(client, IAdminClient)

        def checkAdminClientConnected():
            if client.state != 'authenticated':
                log.warn('XMPP admin client has not been able to authenticate. ' \
                    'Client state is "%s". Will retry on the next request.' % client.state)
                gsm.unregisterUtility(client, IAdminClient)

        zr = getUtility(IZopeReactor)
        zr.reactor.callLater(10, checkAdminClientConnected)


def adminConnected(event):
    log.info('XMPP admin client has authenticated succesfully.')
    # Register user subscribers
    import user_management
    gsm = getGlobalSiteManager()
    gsm.registerHandler(user_management.onUserCreation)
    gsm.registerHandler(user_management.onUserDeletion)


def adminDisconnected(event):
    client = queryUtility(IAdminClient)
    zr = getUtility(IZopeReactor)
    if zr.reactor.running:
        log.warn('XMPP admin client disconnected.')
    gsm = getGlobalSiteManager()
    gsm.unregisterUtility(client, IAdminClient)


