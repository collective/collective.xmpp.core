import logging
from plone.registry.interfaces import IRegistry
from zope.component import (
    getGlobalSiteManager,
    getUtility,
    queryUtility
)
from zope.component.hooks import getSite
from Products.CMFCore.utils import getToolByName
from collective.xmpp.core.client import AdminClient
from collective.xmpp.core.interfaces import (
    IAdminClient,
    IXMPPSettings,
    IProductLayer,
    IZopeReactor
)

log = logging.getLogger(__name__)

def createAdminClient(callback):
    registry = getUtility(IRegistry)
    settings = registry.forInterface(IXMPPSettings, check=False)
    try:
        jid = settings.admin_jid
        password = settings.admin_password
        host = settings.hostname
        port = settings.port
    except KeyError:
        return
    client = AdminClient(jid, host, password, port)
    gsm = getGlobalSiteManager()
    gsm.registerUtility(client, IAdminClient)
    zr = getUtility(IZopeReactor)
    zr.reactor.callLater(10, callback, client)


def setUpAdminClient(event):
    if not IProductLayer.providedBy(event.request):
        return
    site = getSite()
    mtool = getToolByName(site, 'portal_membership', None)
    if not mtool or mtool.isAnonymousUser():
        return
    client = queryUtility(IAdminClient)
    if client is None:

        def checkAdminClientConnected(client):
            if client.state != 'authenticated':
                log.warn('XMPP admin client has not been able to authenticate. ' \
                    'Client state is "%s". Will retry on the next request.' % client.state)
                gsm = getGlobalSiteManager()
                gsm.unregisterUtility(client, IAdminClient)

        createAdminClient(checkAdminClientConnected)


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


