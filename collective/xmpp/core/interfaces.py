from zope.component.interfaces import IObjectEvent
from zope.interface import Interface
from zope.interface import implements
from zope.viewlet.interfaces import IViewletManager

class IProductLayer(Interface):
    """ Marker interface for requests indicating the staralliance.theme
        package has been installed.
    """

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
    """Marker interface for the PubSub twisted client.
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
