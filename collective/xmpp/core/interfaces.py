from collective.xmpp.core import messageFactory as _
from z3c.form import button
from zope import schema
from zope.interface import Interface


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

    update_selected_vcards = button.Button(
        title=_(u'label_update_selected_vcards',
                default=u"Update selected users' vCards"),
        description=_(
            u"help_update_selected_vcards",
            default=u"Click here to update the vCards of the above selected "
            "users in the site."),
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


class IXMPPSettings(Interface):
    """ Global XMPP settings. This describes records stored in the
        configuration registry and obtainable via plone.registry.
    """
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

    bosh_url = schema.TextLine(
        title=_(u"label_xmpp_bosh_url",
                default=u"BOSH URL"),
        description=_(
            u"help_xmpp_bosh_url",
            default=u"The BOSH URL as exposed by your XMPP server."),
        required=True,
        default=u'http://localhost:5280/http-bind',
    )

    debug = schema.Bool(
        title=_(u"label_xmpp_debug",
                default=u"Debug"),
        description=_(
            u"help_xmpp_debug",
            default=u"Enable debug logging in the browser console."),
        default=False,
    )


class IXMPPUsers(Interface):
    """ Marker interface for the XMPP tool.
    """
