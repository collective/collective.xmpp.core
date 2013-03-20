from Products.CMFCore.FSImage import FSImage
from Products.CMFCore.utils import getToolByName
from Products.PluggableAuthService.interfaces import events
from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import IProductLayer
from collective.xmpp.core.interfaces import IXMPPPasswordStorage
from collective.xmpp.core.interfaces import IXMPPUsers
from collective.xmpp.core.utils import setup
from collective.xmpp.core.utils import users
from plone.app.controlpanel.interfaces import IConfigurationChangedEvent
from plone.app.linkintegrity.interfaces import IOFSImage
from plone.app.users.browser.personalpreferences import UserDataPanel
from zope.component import adapter
from zope.component import getUtility
from zope.component.hooks import getSite
from zope.globalrequest import getRequest
import logging

log = logging.getLogger(__name__)


@adapter(IConfigurationChangedEvent)
def onUserPreferencesChanged(event):
    """ Update user's vcard when their prefs have changed.
    """
    request = getRequest()
    if not IProductLayer.providedBy(request):
        return
    if not isinstance(event.context, UserDataPanel):
        return
    portal = getSite()
    mtool = getToolByName(portal, 'portal_membership')
    member = mtool.getAuthenticatedMember()
    member_id = member.getId()
    pass_storage = getUtility(IXMPPPasswordStorage)
    member_pass = pass_storage.get(member_id)
    if not member_pass:
        log.info('%s is not registered on the XMPP server.' % member_id)
        return
    xmpp_users = getUtility(IXMPPUsers)
    member_jid = xmpp_users.getUserJID(member_id)
    portal_url = getToolByName(portal, 'portal_url')()
    fullname = member.getProperty('fullname').decode('utf-8')
    portrait = mtool.getPersonalPortrait(member_id)
    if IOFSImage.providedBy(portrait):
        raw_image = portrait.data
    elif isinstance(portrait, FSImage):
        raw_image = portrait._data
    else:
        log.warn('Could not get the raw data for portrait image for user %s' \
                 % member_id)
        raw_image = None
    udict = {
        'fullname': fullname,
        'nickname': member_id,
        'email': member.getProperty('email'),
        'userid': member_jid.userhost(),
        'jabberid': member_jid.userhost(),
        'url': '%s/author/%s' % (portal_url, member_id),
        'image_type': portrait.content_type,
        'raw_image': raw_image
    }
    setup.setVCard(udict, member_jid, member_pass)


@adapter(events.IPrincipalDeletedEvent)
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



