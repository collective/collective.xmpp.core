import logging
from zope.component import (
    adapter,
    getUtility
)
from zope.globalrequest import getRequest
from Products.PluggableAuthService.interfaces.events import (
    IPrincipalCreatedEvent,
    IPrincipalDeletedEvent
)
from plone.registry.interfaces import IRegistry
from collective.xmpp.core.interfaces import (
    IAdminClient,
    IProductLayer,
    IXMPPPasswordStorage,
    IXMPPSettings,
    IXMPPUsers
)
from collective.xmpp.core.utils import users

log = logging.getLogger(__name__)

@adapter(IPrincipalCreatedEvent)
def onUserCreation(event):
    """ Create a jabber account for new user.
    """
    request = getRequest()
    if not IProductLayer.providedBy(request):
        return

    client = getUtility(IAdminClient)
    xmpp_users = getUtility(IXMPPUsers)
    principal = event.principal

    principal_id = principal.getUserId()
    principal_jid = xmpp_users.getUserJID(principal_id)
    pass_storage = getUtility(IXMPPPasswordStorage)
    principal_pass = pass_storage.set(principal_id)

    registry = getUtility(IRegistry)
    settings = registry.forInterface(IXMPPSettings, check=False)

    users.setupPrincipal(client, principal_jid, principal_pass)


@adapter(IPrincipalDeletedEvent)
def onUserDeletion(event):
    """ Delete jabber account when a user is removed.
    """
    request = getRequest()
    if not IProductLayer.providedBy(request):
        return

    client = getUtility(IAdminClient)
    xmpp_users = getUtility(IXMPPUsers)

    principal_id = event.principal
    principal_jid = xmpp_users.getUserJID(principal_id)

    pass_storage = getUtility(IXMPPPasswordStorage)
    pass_storage.remove(principal_id)

    d = users.deletePrincipal(client, principal_jid)
    return d
