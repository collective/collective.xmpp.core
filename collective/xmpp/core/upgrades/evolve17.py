""" Add a new entry in portal_registry
"""
from zope.component import getUtility
from plone.registry.record import Record
from plone.registry import field
from plone.registry.interfaces import IRegistry
import logging

logger = logging.getLogger("eea.app.visualization.upgrades")

def update_registry(context):
    """ Added new entry in portal_registry regarding auto_register
        general setting
    """
    registry = getUtility(IRegistry)

    if not 'collective.xmpp.core.interfaces.IXMPPSettings.auto_register' in registry.records.keys():
        registry.records['collective.xmpp.core.interfaces.IXMPPSettings.auto_register'] = \
             Record(field.Bool(title=u"Auto-register Plone users"), False)
        logger.info("collective.xmpp.core.interfaces.IXMPPSettings.auto_register \
                     registered under portal_registry")
    else:
        logger.info("collective.xmpp.core.interfaces.IXMPPSettings.auto_register \
                     already registered under portal_registry")
