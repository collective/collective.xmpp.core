from zope.component.hooks import getSite
from zope.component import getUtility
from Products.CMFCore.utils import getToolByName
from plone.registry.interfaces import IRegistry

def getAllMemberIds():
    """ Call searchUsers from PluggableAuthService, so that we get users from
        PAS plugins as well (e.g LDAP).
    """
    portal = getSite()
    acl_users = getToolByName(portal, 'acl_users')
    return [m['userid'] for m in acl_users.searchUsers()]

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

def setupPrincipal(client,
                   principal_jid, principal_password,
                   roster_jids):
    """Create a jabber account for a new user as well
       as create and configure its associated nodes."""
    site = getSite()

    def subscribeToAllUsers(result):
        if result == False:
            return False
        if roster_jids:
            client.chat.sendRosterItemAddSuggestion(principal_jid, roster_jids, site)
        return True

    d = client.admin.addUser(principal_jid.userhost(), principal_password)

    registry = getUtility(IRegistry)
    if registry['collective.xmpp.autoSubscribe']:
        d.addCallback(subscribeToAllUsers)

    return d


def deletePrincipal(client, principal_jid):
    """Delete a jabber account as well as remove its associated nodes.
    """
    principal_id = principal_jid.user
    d = client.admin.deleteUsers(principal_jid.userhost())

    # def deleteUser(result):
    #     if result == False:
    #         return False
    #     d = client.admin.deleteUsers(principal_jid.userhost())
    #     return d

    # d = client.deleteNode(principal_id)
    # d.addCallback(deleteUser)
    # return d
    pass
