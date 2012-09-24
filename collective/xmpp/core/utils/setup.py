import logging

from zope.component import getUtility
from Products.CMFCore.utils import getToolByName

from collective.xmpp.core.interfaces import IXMPPPasswordStorage
from collective.xmpp.core.interfaces import IXMPPUsers

log = logging.getLogger(__name__)

def setupXMPPEnvironment(context):
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

