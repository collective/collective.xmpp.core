from collective.xmpp.core.interfaces import IXMPPSettings
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
import logging

log = logging.getLogger(__name__)


def setVCard(udict, jid, password, callback=None):

    def onAuth():
        client.vcard.send(udict, disconnect)

    from collective.xmpp.core.client import UserClient
    registry = getUtility(IRegistry)
    settings = registry.forInterface(IXMPPSettings, check=False)
    client = UserClient(
        jid,
        settings.hostname,
        password,
        settings.port,
        onAuth
    )

    def disconnect(result):
        client.disconnect()
        log.info('Successfully added a VCard')
        if callback and hasattr(callback, '__call__'):
            callback()
