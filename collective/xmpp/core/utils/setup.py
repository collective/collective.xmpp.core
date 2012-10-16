import logging

from zope.component import getUtility
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName

from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import IXMPPPasswordStorage
from collective.xmpp.core.interfaces import IXMPPUsers
from collective.xmpp.core.utils.users import setupPrincipal

log = logging.getLogger(__name__)

def setupXMPPEnvironment(context):
    client = getUtility(IAdminClient)
    registry = getUtility(IRegistry)
    xmpp_users = getUtility(IXMPPUsers)
    pass_storage = getUtility(IXMPPPasswordStorage)
    mt = getToolByName(context, 'portal_membership')
    member_ids = mt.listMemberIds()
    member_jids = []
    member_passwords = {}
    pass_storage.clear()
    for member_id in member_ids:
        member_jid = xmpp_users.getUserJID(member_id)
        member_jids.append(member_jid)
        member_passwords[member_jid] = pass_storage.set(member_id)
        member_pass = pass_storage.set(member_id)

        if registry['collective.xmpp.autoSubscribe']:
            mtool = getToolByName(context, 'portal_membership')
            members_jids = [xmpp_users.getUserJID(member.getUserId())
                            for member in mtool.listMembers()]
        else:
            members_jids = []
        d = setupPrincipal(client, member_jid, member_pass, members_jids)
