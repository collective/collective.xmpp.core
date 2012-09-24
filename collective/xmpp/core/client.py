import logging

from twisted.words.protocols.jabber.jid import JID
from zope.event import notify
from zope.interface import implements
from wokkel.xmppim import PresenceClientProtocol

from jarn.xmpp.twisted.client import XMPPClient
from jarn.xmpp.twisted.protocols import AdminHandler
from jarn.xmpp.twisted.protocols import ChatHandler

from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import AdminClientConnected
from collective.xmpp.core.interfaces import AdminClientDisconnected


logger = logging.getLogger(__name__)

class AdminClient(XMPPClient):

    implements(IAdminClient)

    def __init__(self, jid, jdomain, password):

        jid = JID(jid)
        self.admin = AdminHandler()
        self.chat = ChatHandler()
        self.presence = PresenceClientProtocol()

        super(AdminClient, self).__init__(
            jid, password,
            extra_handlers=[self.admin,
                            self.chat,
                            self.presence],
            host=jdomain)

    def _authd(self, xs):
        super(AdminClient, self)._authd(xs)
        self.presence.available()
        ev = AdminClientConnected(self)
        notify(ev)

    def _disconnected(self, reason):
        super(AdminClient, self)._disconnected(reason)
        ev = AdminClientDisconnected(self)
        notify(ev)
