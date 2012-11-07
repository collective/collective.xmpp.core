from zope import schema
from zope.component.interfaces import IObjectEvent
from zope.interface import Interface
from zope.interface import implements
from zope.viewlet.interfaces import IViewletManager
from z3c.form import button

from collective.xmpp.core import messageFactory as _

class IProductLayer(Interface):
    """ Marker interface for requests indicating the staralliance.theme
        package has been installed.
    """

class IXMPPUserSetup(Interface):
    """ 
    """
    users = schema.List(
        title=_(u"label_users", default=u"Choose Users"),
        description=_(u"help_user_setup",
                default=u"Choose here the users you'd like to register "
                        u"or deregister from the XMPP server."),
        value_type=schema.TextLine(),
        required=False,
        )

    register_selected = button.Button(
                            title=_(u'label_register_selected',
                                default=u"Register Selected Users"),
                            description=_(u"help_register_selected", 
                                default=u"Click this button to let the above "
                                "selected users be registered on the XMPP "
                                "server."),
                            required=False,
                            )
    deregister_selected = button.Button(
                            title=_(u'label_deregister_selected',
                                default=u"Deregister Selected Users"),
                            description=_(u"help_deregister_selected",
                                default=u"Click this button to deregister the "
                                "above selected users from the XMPP server."),
                            required=False,
                            )
    register_all = button.Button(
                            title=_(u'label_register_all',
                                default=u"Register ALL Users"),
                            description=_(u"help_register_all", 
                                default=u"Click this button to register ALL "
                                "the users in the site on the XMPP "
                                "server. WARNING: This should only ever be done "
                                "once, unless you know what you're doing!"),
                            required=False,
                            )
    deregister_all = button.Button(
                            title=_(u'label_deregister_all',
                                default=u"Deregister ALL Users"),
                            description=_(u"help_deregister_all",
                                default=u"Click this button to deregister ALL "
                                "the users in the site from the XMPP server."),
                            required=False,
                            )


class IXMPPSettings(Interface):
    """ Global XMPP settings. This describes records stored in the
        configuration registry and obtainable via plone.registry.
    """
    xmpp_domain = schema.TextLine(
        title=_(u"label_xmpp_domain",
                default=u"XMPP Domain"),
        description=_(u"help_xmpp_domain",
                default=u"The domain under which your XMPP server is running."),
        required=True,
        default=u'localhost',
        )

    admin_jid = schema.TextLine(
        title=_(u"label_xmpp_admin_jid",
                default=u"XMPP Admin JID"),
        description=_(u"help_xmpp_admin_jid",
                default=u"The Jabber ID of an XMPP user with administration "
                        u"rights. Plone uses this user to manage (e.g "
                        u"register/unregister) other XMPP users."),
        required=True,
        default=u'admin@localhost',
        )

    admin_password = schema.Password(
        title=_(u"label_xmpp_admin_password",
                default="XMPP Admin Password"),
        required=True,
        default=u'admin',
        )

    auto_subscribe = schema.Bool( 
        title=_(u"label_xmpp_auto_subscribe",
                default=u"Auto-subscribe XMPP users"),
        description=_(u"help_xmpp_auto_subscribe",
                default=u"Should XMPP users automatically be subscribed to one "
                        u"another? "
                        u"Users will automatically subscribe to all other XMPP "
                        u"users in the site, but each subscription will only "
                        u"be confirmed once the user being subscribed to logs "
                        u"in. Be aware that this is probably a bad idea on "
                        u"sites with many users!"),
        default=False,
        )



class IZopeReactor(Interface):
    """Initializes and provides the twisted reactor.
    """


class IDeferredXMPPClient(Interface):
    """ Marker interface for the DeferredXMPPClient utility.
    """


class IReactorStarted(IObjectEvent):
    """Reactor has been started.
    """


class ReactorStarted(object):
    implements(IReactorStarted)

    def __init__(self, obj):
        self.object = obj


class IReactorStoped(IObjectEvent):
    """Reactor has been stoped.
    """


class ReactorStoped(object):
    implements(IReactorStoped)

    def __init__(self, obj):
        self.object = obj


class IXMPPUsers(Interface):
    """ Marker interface for the XMPP tool.
    """


class IXMPPPasswordStorage(Interface):
    """ Marker interface for the xmmp user passwords
    """


class IPubSubable(Interface):
    """Interface for objects that can be uniquely linked to pubsub nodes.
    """


class IPubSubStorage(Interface):
    """Marker interface for the PubSub storage
    """


class IAdminClient(Interface):
    """Marker interface for the twisted client.
    """


class IAdminClientConnected(IObjectEvent):
    """Admin client has connected.
    """


class AdminClientConnected(object):
    implements(IAdminClientConnected)

    def __init__(self, obj):
        self.object = obj


class IAdminClientDisconnected(IObjectEvent):
    """Admin client has connected.
    """


class AdminClientDisconnected(object):
    implements(IAdminClientConnected)

    def __init__(self, obj):
        self.object = obj


class IXMPPLoaderVM(IViewletManager):
    """Viewlet manager for the loader viewlet.
    """
