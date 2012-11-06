import logging
import transaction
import Zope2

from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.component.hooks import setSite
from plone.registry.interfaces import IRegistry

from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import IXMPPPasswordStorage
from collective.xmpp.core.interfaces import IXMPPUsers
from collective.xmpp.core.subscribers.startup import createAdminClient
from collective.xmpp.core.utils import users

log = logging.getLogger(__name__)


def setupXMPPEnvironment(portal):
    """ Register each Plone user in the XMPP server and save his/her password.

        If users auto-subscribe to one another, we need to send roster item add
        suggestions containing all the XMPP users.

        Since we only have all the XMPP users available once every single user
        has been registered there, we need to make use of deferred objects and
        ensure that the suggestion is sent only when every user has been
        registered on the XMPP server.
    """
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

    registry = getUtility(IRegistry)
    xmpp_users = getUtility(IXMPPUsers)
    pass_storage = getUtility(IXMPPPasswordStorage)
    member_ids = users.getAllMemberIds() 
    member_jids = []
    member_passwords = {}
    pass_storage.clear()

    def subscribeToAllUsers():
        for member_jid in member_jids:
            client.chat.sendRosterItemAddSuggestion(member_jid, member_jids, portal)
        return True

    def registerUser():
        if not member_ids:
            if registry['collective.xmpp.autoSubscribe']:
                subscribeToAllUsers()
            return
        member_id = member_ids.pop()
        member_jid = xmpp_users.getUserJID(member_id)
        member_jids.append(member_jid)
        member_pass = pass_storage.set(member_id)
        d = client.admin.addUser(member_jid.userhost(), member_pass)
        d.addCallback(registerNextUser)

    def registerNextUser(result):
        if result is False:
            return 

        if getSite():
            registerUser()
        else:
            app = Zope2.app()
            root = app.unrestrictedTraverse('/'.join(portal.getPhysicalPath()))
            setSite(root)
            transaction.begin()
            try:
                registerUser()
                transaction.commit()
            except Exception, e:
                log.error(e)
                transaction.abort()
            finally:
                setSite(None)
                app._p_jar.close()
        return True

    registerNextUser(True)
