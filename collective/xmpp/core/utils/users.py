import logging
from wokkel.disco import NS_DISCO_ITEMS
from twisted.words.protocols.jabber.jid import JID
from twisted.words.protocols.jabber.xmlstream import IQ
from zope.component.hooks import getSite
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError
from Products.CMFCore.utils import getToolByName
from plone.registry.interfaces import IRegistry
from collective.xmpp.core.interfaces import IXMPPSettings

log = logging.getLogger(__name__)

def getXMPPDomain(portal=None):
    try:
        registry = getUtility(IRegistry)
    except ComponentLookupError:
        portal = portal or getSite()
        registry = getUtility(IRegistry, context=portal)
    settings = registry.forInterface(IXMPPSettings, check=False)
    return settings.xmpp_domain

def getAllMemberIds():
    """ Call searchUsers from PluggableAuthService, so that we get
        users from PAS plugins as well (e.g LDAP)
    """
    portal = getSite()
    acl_users = getToolByName(portal, 'acl_users')
    return list(set([m['userid'] for m in acl_users.searchUsers()]))

def escapeNode(node):
    """ Escape the node part (also called local part) of a JID.
        See: http://xmpp.org/extensions/xep-0106.html#escaping
    """
    node.strip()
    node = node.replace('\\', "\\5c")
    node = node.replace(' ',  "\\20")
    node = node.replace('\"', "\\22")
    node = node.replace('\&', "\\26")
    node = node.replace('\'', "\\27")
    node = node.replace('\/', "\\2f")
    node = node.replace(':',  "\\3a")
    node = node.replace('<',  "\\3c")
    node = node.replace('>',  "\\3e")
    node = node.replace('@',  "\\40");
    return node

def unescapeNode(node):
    """ Unescape the node part (also called local part) of a JID.
        See: http://xmpp.org/extensions/xep-0106.html#escaping
    """
    node = node.replace("\\5c", '\\')
    node = node.replace("\\20", ' ')
    node = node.replace("\\22", '\"')
    node = node.replace("\\26", '\&')
    node = node.replace("\\27", '\'')
    node = node.replace("\\2f", '\/')
    node = node.replace("\\3a", ':')
    node = node.replace("\\3c", '<')
    node = node.replace("\\3e", '>')
    node = node.replace("\\40", '@')
    return node

def deletePrincipal(client, principal_jid):
    """ Delete a jabber account as well as remove its associated nodes
    """
    d = client.admin.deleteUsers(principal_jid.userhost())

    # XXX: PubSub stuff.
    # def deleteUser(result):
    #     if result == False:
    #         return False
    #     d = client.admin.deleteUsers(principal_jid.userhost())
    #     return d
    # principal_id = principal_jid.user
    # d = client.deleteNode(principal_id)
    # d.addCallback(deleteUser)
    # return d
    pass

