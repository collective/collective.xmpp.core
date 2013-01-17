import logging
from plone.registry.interfaces import IRegistry
from twisted.words.protocols.jabber.jid import JID
from zope.component import getUtility
from zope.interface import implements
from collective.xmpp.core.interfaces import IXMPPPasswordStorage
from collective.xmpp.core.interfaces import IXMPPSettings
from collective.xmpp.core.interfaces import IXMPPUsers
from collective.xmpp.core.utils.users import escapeNode

log = logging.getLogger(__name__)

class XMPPUsers(object):
    implements(IXMPPUsers)

    def getUserJID(self, user_id):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IXMPPSettings, check=False)
        return JID("%s@%s" % (escapeNode(user_id), settings.xmpp_domain))

    def getUserPassword(self, user_id):
        pass_storage = getUtility(IXMPPPasswordStorage)
        return pass_storage.get(user_id)
