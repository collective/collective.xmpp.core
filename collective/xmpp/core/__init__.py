from twisted.python.log import addObserver
from zope.i18nmessageid import MessageFactory
import logging

log = logging.getLogger(__name__)
messageFactory = MessageFactory('collective.xmpp.core')


def observer(data):
    func = data['isError'] and log.warn or log.info
    for m in data['message']:
        func('Twisted: %s' % m)

addObserver(observer)
