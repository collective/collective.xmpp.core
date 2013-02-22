import logging
import transaction
import Zope2
from twisted.words.protocols.jabber.jid import JID
from twisted.words.protocols.jabber.xmlstream import IQ

from wokkel.disco import NS_DISCO_ITEMS
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.component.hooks import setSite

from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName

from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import IXMPPPasswordStorage
from collective.xmpp.core.interfaces import IXMPPSettings
from collective.xmpp.core.interfaces import IXMPPUsers
from collective.xmpp.core.interfaces import IZopeReactor
from collective.xmpp.core.subscribers.startup import createAdminClient
from collective.xmpp.core.utils.users import escapeNode
from collective.xmpp.core.utils.users import getXMPPDomain 

log = logging.getLogger(__name__)


def registerXMPPUsers(portal, member_ids):
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
            registerXMPPUsers(portal, member_ids)
            setSite(None)

        createAdminClient(checkAdminClientConnected)
        return

    mtool = getToolByName(portal, 'portal_membership')
    registry = getUtility(IRegistry)
    settings = registry.forInterface(IXMPPSettings, check=False)
    xmpp_users = getUtility(IXMPPUsers)
    pass_storage = getUtility(IXMPPPasswordStorage)
    zr = getUtility(IZopeReactor)
    member_jids = []
    member_passwords = {}

    def subscribeToAllUsers():
        def getUserJID(user_id):
            return JID("%s@%s" % (escapeNode(user_id), settings.xmpp_domain))

        def resultReceived(result):
            items = [item.attributes for item in result.query.children]
            if items[0].has_key('node'):
                for item in reversed(items):
                    iq = IQ(client.admin.xmlstream, 'get')
                    iq['to'] = getXMPPDomain(portal) 
                    query = iq.addElement((NS_DISCO_ITEMS, 'query'))
                    query['node'] = item['node']
                    iq.send().addCallbacks(resultReceived)
            else:
                subscribe_jids = [item['jid'] for item in items]
                if settings.admin_jid in subscribe_jids:
                    subscribe_jids.remove(settings.admin_jid)
                if subscribe_jids:
                    roster_jids = [getUserJID(user_id.split('@')[0])
                                     for user_id in subscribe_jids]

                    for member_jid in member_jids:
                        client.chat.sendRosterItemAddSuggestion(member_jid,
                                                                roster_jids,
                                                                portal)
            return result
        d = client.admin.getRegisteredUsers()
        d.addCallbacks(resultReceived)
        return True

    def setVCard(member, callback):
        from collective.xmpp.core.client import UserClient
        user_id = member.getId()
        fullname = member.getProperty('fullname')
        user_jid = xmpp_users.getUserJID(user_id)
        user_pass  = xmpp_users.getUserPassword(user_id)
        # TODO:
        # portrait_url = pm.getPersonalPortrait(user_id).absolute_url()
        # portal_url = getToolByName(self.context, 'portal_url')
        # user_profile_url = '%s/author/%s' % (portal_url(), user_id)
        udict = {
            'fullname': fullname,
            'nickname': user_id,
            'email': member.getProperty('email'),
            'userid': user_jid.userhost(),
            'jabberid': user_jid.userhost(),
            }
        userclient = UserClient(
                            user_jid, 
                            settings.hostname, 
                            user_pass, 
                            settings.port)

        def checkClientConnected(client):
            if client.state != 'authenticated':
                log.warn('XMPP user client has not been able to authenticate. ' \
                    'This means the VCard could not be set. ' \
                    'Client state is "%s".' % client.state)
            else:
                client.vcard.send(udict, callback)
        zr.reactor.callLater(10, checkClientConnected, userclient)

    def registerUser():
        if not member_ids:
            if settings.auto_subscribe:
                subscribeToAllUsers()
            return
        member_id = member_ids.pop()
        member_jid = xmpp_users.getUserJID(member_id)
        member_jids.append(member_jid)
        member_pass = pass_storage.set(member_id)
        d = client.admin.addUser(member_jid.userhost(), member_pass)
        member = mtool.getMemberById(member_id)
        setVCard(member, registerNextUser)

    def registerNextUser(result):
        if hasattr(result, 'handled') and result.handled:
            log.info('Successfully added a VCard')
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


def deregisterXMPPUsers(portal, member_jids):
    """ Deregister each Plone user from the XMPP
    """
    log.info('Preparing to remove XMPP users')
    client = queryUtility(IAdminClient, context=portal)
    if client is None:
        log.info('We first have to create the XMPP admin client. '
                 'This might take a few seconds')

        def checkAdminClientConnected(client):
            if client.state != 'authenticated':
                log.warn('XMPP admin client has not been able to authenticate. ' \
                    'Client state is "%s". Will retry on the next request.' % client.state)
                gsm = getGlobalSiteManager()
                gsm.unregisterUtility(client, IAdminClient)
            deregisterXMPPUsers(portal, member_jids)
            setSite(None)

        createAdminClient(checkAdminClientConnected)
        return

    # Clear passwords
    passwords = queryUtility(IXMPPPasswordStorage, context=portal)
    if passwords:
        for member_jid in member_jids:
            if isinstance(member_jid, JID):
                member_jid = member_jid.userhost()
            member_id = member_jid.rsplit('@')[0]
            passwords.remove(member_id)

    client.admin.deleteUsers(member_jids)
    transaction.commit()
