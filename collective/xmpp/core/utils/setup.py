import logging
import transaction
import Zope2

from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.component.hooks import setSite
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName

from collective.xmpp.core.subscribers.startup import createAdminClient
from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import IXMPPPasswordStorage
from collective.xmpp.core.interfaces import IXMPPUsers

log = logging.getLogger(__name__)


def setupXMPPEnvironment(portal):
    log.info('Preparing to create XMPP users from the existing Plone users')

    client = queryUtility(IAdminClient)
    if client is None:
        log.info('We first have to create the XMPP admin client. '
                 'This might take a few seconds')

        def checkAdminClientConnected(client):
            if client.state != 'authenticated':
                log.warn('XMPP admin client has not been able to authenticate. ' \
                    'Client state is "%s". Will retry on the next request.' % client.state)
                gsm = getGlobalSiteManager()
                gsm.unregisterUtility(client, IAdminClient)
            setupXMPPEnvironment(portal)
            setSite(None)

        createAdminClient(checkAdminClientConnected)
        return

    app = Zope2.app()
    transaction.begin()
    setSite(portal)

    registry = getUtility(IRegistry)
    xmpp_users = getUtility(IXMPPUsers)
    pass_storage = getUtility(IXMPPPasswordStorage)
    mt = getToolByName(portal, 'portal_membership')
    member_ids = mt.listMemberIds()
    member_jids = []
    member_passwords = {}
    pass_storage.clear()

    def subscribeToAllUsers():
        for member_jid in member_jids:
            client.chat.sendRosterItemAddSuggestion(member_jid, member_jids)
        return True

    def registerNextUser(result):
        if result is False:
            return 

        app = Zope2.app()
        setSite(portal)
        transaction.begin()

        if not member_ids:
            if registry['collective.xmpp.autoSubscribe']:
                subscribeToAllUsers()
            return

        member_id = member_ids.pop()
        member_jid = xmpp_users.getUserJID(member_id)
        member_jids.append(member_jid)

        member_passwords[member_jid] = pass_storage.set(member_id)
        member_pass = pass_storage.set(member_id)
        d = client.admin.addUser(member_jid.userhost(), member_pass)
        d.addCallback(registerNextUser)
        setSite(None)
        transaction.commit()
        app._p_jar.close()
        return True

    registerNextUser(True)
    transaction.commit()
    app._p_jar.close()
