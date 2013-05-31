from collective.xmpp.core import messageFactory as _
from z3c.form import button
from zope import schema
from zope.component.interfaces import IObjectEvent
from zope.interface import Interface
from zope.interface import implements
from zope.viewlet.interfaces import IViewletManager

class IProductLayer(Interface):
    """ Marker interface for requests indicating the staralliance.theme
        package has been installed.
    """


class IXMPPUserSetup(Interface):
    """
    """
    users = schema.List(
        title=_(u"label_users", default=u"Choose Users"),
        description=_(
            u"help_user_setup",
            default=u"Choose here the users you'd like to register "
                    u"or deregister from the XMPP server."),
        value_type=schema.TextLine(),
        required=True,
    )

    register_selected = button.Button(
        title=_(u'label_register_selected',
                default=u"Register Selected Users"),
        description=_(
            u"help_register_selected",
            default=u"Click this button to let the above "
            "selected users be registered on the XMPP "
            "server. Already registered users will be "
            "ignored."),
        required=False,
    )

    deregister_selected = button.Button(
        title=_(u'label_deregister_selected',
                default=u"Deregister Selected Users"),
        description=_(
            u"help_deregister_selected",
            default=u"Click this button to deregister the "
            "above selected users from the XMPP server."),
        required=False,
    )

    register_all = button.Button(
        title=_(u'label_register_all',
                default=u"Register ALL Users"),
        description=_(
            u"help_register_all",
            default=u"Click this button to register ALL "
            "the users in the site on the XMPP "
            "server. Already registered users will be "
            "ignored. BE AWARE: if you register lots "
            "of users and have auto-subscribe turned on, "
            "your Plone server will be very busy with multiple "
            "threads and may become unresponsive for some "
            "minutes."),
        required=False,
    )

    deregister_all = button.Button(
        title=_(u'label_deregister_all',
                default=u"Deregister ALL Users"),
        description=_(
            u"help_deregister_all",
            default=u"Click this button to deregister ALL "
            "the users in the site from the XMPP server."),
        required=False,
    )

    update_vcards = button.Button(
        title=_(u'label_update_vcards',
                default=u"Update ALL Users' vCards"),
        description=_(
            u"help_update_vcards",
            default=u"Click here to update the vCards of ALL "
            "the users in the site."),
        required=False,
    )


    # XXX: Useful in certain circumstances, but dangerous and should probably
    # not be available by default.
    #
    # clear_all_passwords = button.Button(
    #     title=_(u'label_clear_passwords',
    #             default=u"Completely wipe password storage"),
    #     description=_(
    #         u"help_clear_passwords",
    #         default=u"DON'T CLICK THIS UNLESS YOU KNOW WHAT "
    #         u"YOU'RE DOING! This will remove ALL the "
    #         u"entries in the XMPP password storage "
    #         u"utility in Plone and should only be useful "
    #         u"in very rare cases or while developing."),
    #     required=False,
    # )


class IXMPPSettings(Interface):
    """ Global XMPP settings. This describes records stored in the
        configuration registry and obtainable via plone.registry.
    """
    xmpp_domain = schema.TextLine(
        title=_(u"label_xmpp_domain",
                default=u"XMPP Domain"),
        description=_(
            u"help_xmpp_domain",
            default=u"The domain which the XMPP server will serve."
            u"This is also the domain under which users are "
            u"registered. XMPP user ids are made up of the plone "
            u"username and domain, like this: ${username}@${domain}."),
        required=True,
        default=u'localhost',
    )

    hostname = schema.TextLine(
        title=_(u"label_server_hostname",
                default=u"XMPP Server Hostname"),
        description=_(
            u"help_server_hostname",
            default=u"The hostname of the server on which the XMPP server "
            u"is running. Useful when you are running your XMPP server "
            u"on the same server, LAN or VPN as your Plone site. "
            u"Otherwise, keep the same as the XMPP domain."),
        required=True,
        default=u'localhost',
    )

    port = schema.Int(
        title=_(u"label_server_port",
                default=u"XMPP Server Port"),
        description=_(
            u"help_server_port",
            default=u"The port number of the XMPP server. Default is 5222."),
        required=True,
        default=5222,
    )

    admin_jid = schema.TextLine(
        title=_(u"label_xmpp_admin_jid",
                default=u"XMPP Admin JID"),
        description=_(
            u"help_xmpp_admin_jid",
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

    auto_register_on_login = schema.Bool(
        title=_(u"label_xmpp_auto_register_on_login",
                default=u"Automatically register for XMPP on login"),
        description=_(
            u"help_xmpp_auto_register_on_login",
            default=u"Check this option if you want users to be "
            u"automatically registered on the XMPP server."
            u"They will be registered once they visit "
            u"this Plone site while logged in."
            u"You can also register users manually on the XMPP "
            u"user setup page."),
        default=False,
    )

    auto_subscribe = schema.Bool(
        title=_(u"label_xmpp_auto_subscribe",
                default=u"Auto-subscribe XMPP users"),
        description=_(
            u"help_xmpp_auto_subscribe",
            default=u"Should XMPP users automatically be subscribed to one "
            u"another? "
            u"Users will automatically subscribe to all other XMPP "
            u"users in the site, but each subscription will only "
            u"be confirmed once the user being subscribed to logs "
            u"in. Be aware that this is probably a bad idea on "
            u"sites with many users!"),
        default=False,
    )

    auto_join = schema.List(
        title=_(u"label_xmpp_auto_join",
                default=u"Auto-join the following chat rooms"),
        description=_(
            u"help_xmpp_auto_join",
            default=u"Users will automatically subscribe to the selected "
            u"chat rooms"),
        value_type=schema.TextLine(required=False),
        required=False
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
