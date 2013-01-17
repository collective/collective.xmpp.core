from wokkel.disco import NS_DISCO_ITEMS
from twisted.words.protocols.jabber.jid import JID
from twisted.words.protocols.jabber.xmlstream import IQ

from zope.component.hooks import getSite
from zope.component import getUtility
from Products.CMFCore.utils import getToolByName
from plone.registry.interfaces import IRegistry

from collective.xmpp.core.interfaces import IXMPPSettings

def getXMPPDomain():
    registry = getUtility(IRegistry)
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

def setupPrincipal(client, principal_jid, principal_password):
    """ Create a jabber account for a new user as well
        as create and configure its associated nodes
    """
    site = getSite()

    def subscribeToAllUsers(result):
        if result == False:
            return False

        def getUserJID(user_id):
            settings = registry.forInterface(IXMPPSettings, check=False)
            return JID("%s@%s" % (escapeNode(user_id), settings.xmpp_domain))

        def resultReceived(result):
            items = [item.attributes for item in result.query.children]
            if items[0].has_key('node'):
                for item in reversed(items):
                    iq = IQ(client.admin.xmlstream, 'get')
                    iq['to'] = getXMPPDomain() 
                    query = iq.addElement((NS_DISCO_ITEMS, 'query'))
                    query['node'] = item['node']
                    iq.send().addCallbacks(resultReceived)
            else:
                member_jids = [item['jid'] for item in items]
                if settings.admin_jid in member_jids:
                    member_jids.remove(settings.admin_jid)
                if member_jids:
                    roster_jids = [getUserJID(user_id.split('@')[0])
                                     for user_id in member_jids]

                    client.chat.sendRosterItemAddSuggestion(principal_jid,
                                                            roster_jids,
                                                            site)

            return result

        d = client.admin.getRegisteredUsers()
        d.addCallbacks(resultReceived)
        return True

    d = client.admin.addUser(principal_jid.userhost(), principal_password)

    registry = getUtility(IRegistry)
    settings = registry.forInterface(IXMPPSettings, check=False)
    if settings.auto_subscribe:
        d.addCallback(subscribeToAllUsers)

    return d


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
