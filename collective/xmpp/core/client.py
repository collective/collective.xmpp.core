import logging
import random
import string

from twisted.words.protocols.jabber.jid import JID
from wokkel import client
from wokkel.subprotocols import StreamManager
from wokkel.xmppim import PresenceClientProtocol

from zope.component import getUtility
from zope.event import notify
from zope.interface import implements

from jarn.xmpp.twisted.interfaces import IDeferredXMPPClient
from jarn.xmpp.twisted.interfaces import IZopeReactor
from jarn.xmpp.twisted.protocols import AdminHandler
from jarn.xmpp.twisted.protocols import ChatHandler

from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import AdminClientConnected
from collective.xmpp.core.interfaces import AdminClientDisconnected

logger = logging.getLogger(__name__)

def randomResource():
    chars = string.letters + string.digits
    resource = 'auto-' + ''.join([random.choice(chars) for i in range(10)])
    return resource


class DeferredXMPPClient(object):
    implements(IDeferredXMPPClient)

    def execute(self, jid, password, host,
                callback, extra_handlers=[], errback=None):

        jid.resource=randomResource()

        factory = client.DeferredClientFactory(jid, password)
        for handler in extra_handlers:
            handler.setHandlerParent(factory.streamManager)

        d = client.clientCreator(factory)

        def disconnect(result):
            factory.streamManager.xmlstream.sendFooter()
            factory.streamManager.xmlstream.transport.connector.disconnect()
            return result

        def defaultErrBack(error_stanza):
            logger.error(error_stanza.getErrorMessage())
            logger.error("StanzaError: %s" % error_stanza.value.stanza.toXml())

        d.addCallback(callback)
        d.addCallback(disconnect)

        if errback:
            d.addErrback(errback)
        else:
            d.addErrback(defaultErrBack)

        zr = getUtility(IZopeReactor)
        zr.reactor.callFromThread(zr.reactor.connectTCP,
                                  host, 5222, factory)
        return d


class XMPPClient(StreamManager):
    """ Service that initiates an XMPP client connection.
    """

    def __init__(self, jid, password, extra_handlers=[],
                 host='localhost', port=5222):

        jid.resource=randomResource()
        self.jid = jid
        self.domain = jid.host
        self.host = host
        self.port = port
        self._state = None
        self._connector = None

        factory = client.HybridClientFactory(jid, password)

        # Setup StreamManager
        StreamManager.__init__(self, factory)
        for handler in extra_handlers:
            handler.setHandlerParent(self)

        self._state = u'connecting'
        zr = getUtility(IZopeReactor)
        zr.reactor.callFromThread(self.connect)

    def connect(self):
        zr = getUtility(IZopeReactor)
        self._connector = zr.reactor.connectTCP(self.host,
                                                self.port,
                                                self.factory)

    def disconnect(self):
        self.xmlstream.sendFooter()
        self._connector.disconnect()

    @property
    def state(self):
        return self._state

    def _authd(self, xs):
        #Save the JID that we were assigned by the server, as the resource
        # might differ from the JID we asked for.
        self.jid = self.factory.authenticator.jid
        StreamManager._authd(self, xs)
        self._state = u'authenticated'

    def _connected(self, xs):
        self._state = u'connected'
        super(XMPPClient, self)._connected(xs)

    def _disconnected(self, _):
        self._state = u'disconnected'
        super(XMPPClient, self)._disconnected(_)


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
