"""
This module enables you to configure your Plone site's registry for
collective.xmpp.core via buildout.

Just add something like the following under the [instance] section of your
buildout (i.e where you configure your plone instance):

zope-conf-additional +=
    <product-config collective.xmpp.core>
        instance_name Plone
        xmpp_domain localhost
        hostname localhost
        port 5222
        admin_jid admin@localhost
        admin_password secret
        auto_subscribe 0 
    </product-config>

WARNING: If you put the above in your buildout.cfg, your plone.registry entries
will be overridden with those values every time you restart your zope server.
In other words, you basically lose the ability to configure your xmpp settings
via Plone itself.
"""
import logging
import transaction
from zope.app.publication.zopepublication import ZopePublication
from zope.component import getUtility
from zope.component.hooks import setSite

from App.config import getConfiguration
from Products.CMFCore.utils import getToolByName
import Zope2

from plone.registry.interfaces import IRegistry
from collective.xmpp.core.interfaces import IXMPPSettings

configuration = getConfiguration()
if not hasattr(configuration, 'product_config'):
    conf = None
else:
    conf = configuration.product_config.get('collective.xmpp.core')

log = logging.getLogger(__name__)

def dbconfig(event):
    """ """
    if conf is None:
        log.error('No product config found! Configuration will not be set')
        return
    db = Zope2.DB
    connection = db.open()
    root_folder = connection.root().get(ZopePublication.root_name, None)
    instance_name = conf.get('instance_name')
    if not instance_name:
        log.error('"instance_name" needs to be set if you want to configure '
                'collective.xmpp.core from buildout.')
        return

    plone = root_folder.get(instance_name)
    if plone is None:
        log.error('No Plone instance with instance_name "%s" found!' % instance_name)
        return

    setup = getToolByName(plone, 'portal_setup')
    try:
        info = setup.getProfileInfo('profile-collective.xmpp.core:default')
    except KeyError:
        log.error('Could not find GS profile for collective.xmpp.core')
        return

    try:
        version = int(info.get('version', 0))
    except KeyError:
        log.error('Could not get intelligible profile version for collective.xmpp.core')
        return

    if version < 2 or True:
        setSite(plone)
        setup.runImportStepFromProfile('profile-collective.xmpp.core:default', 'plone.app.registry')
        setSite(None)

    registry = getUtility(IRegistry, context=plone)
    settings = registry.forInterface(IXMPPSettings, check=False)
    settings.xmpp_domain = unicode(conf.get('xmpp_domain', u'localhost'))
    settings.hostname = unicode(conf.get('hostname', u'localhost'))
    settings.port = int(conf.get('port', 5222))
    settings.admin_jid = unicode(conf.get('admin_jid', u'admin@localhost'))
    settings.admin_password = unicode(conf.get('admin_password', u'secret'))
    settings.auto_subscribe = bool(int(conf.get('auto_subscribe'), 0))
    transaction.commit()
