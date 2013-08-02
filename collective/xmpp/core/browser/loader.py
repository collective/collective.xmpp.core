from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from collective.xmpp.core.client import randomResource
from collective.xmpp.core.httpb import BOSHClient
from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import IXMPPPasswordStorage
from collective.xmpp.core.interfaces import IXMPPSettings
from collective.xmpp.core.interfaces import IXMPPUsers
from collective.xmpp.core.utils import setup
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
import json
import logging

log = logging.getLogger(__name__)


class XMPPLoader(BrowserView):
    """ """
    bind_retry = False

    def autoRegister(self, client):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IXMPPSettings, check=False)
        if not settings.auto_register_on_login or \
                client._state == 'connecting':
            return
        setup.registerXMPPUsers(getSite(), [self.user_id])
        self.bind_retry = True

    def available(self, resource=None):
        self._available = True
        client = queryUtility(IAdminClient)
        if client is None:
            self._available = False
            return
        pm = getToolByName(self.context, 'portal_membership')
        self.user_id = pm.getAuthenticatedMember().getId()
        if self.user_id is None:
            self._available = False
            return
        self.xmpp_users = getUtility(IXMPPUsers)
        self.jid = self.xmpp_users.getUserJID(self.user_id)
        if resource is None:
            self.jid.resource = randomResource()
        else:
            self.jid.resource = resource

        registry = getUtility(IRegistry)
        settings = registry.forInterface(IXMPPSettings, check=False)
        if self.jid.userhost() == settings.admin_jid:
            # The admin user's password is not stored in the
            # IXMPPPasswordStorage utility, so we get it from IXMPPSettings
            self.jpassword = settings.admin_password
        else:
            self.jpassword = self.xmpp_users.getUserPassword(self.user_id)

        if self.jpassword is None:
            self._available = False
            self.autoRegister(client)
        return self._available

    @property
    def bosh(self):
        return self.context.REQUEST.get('SERVER_URL') + '/http-bind'

    def prebind(self):
        b_client = BOSHClient(self.jid, self.jpassword, self.bosh)
        session = b_client.startSession()
        if session:
            if type(session) == tuple:
                return session[1], session[1]
            return b_client.rid, b_client.sid
        return '', ''

    def __call__(self, resource=None):
        bosh_credentials = {}
        available = self.available(resource)
        if self.bind_retry:
            # Try one more time to bind users registered on login
            bosh_credentials = {
                'bind_retry': True,
            }
        if available:
            rid, sid = self.prebind()
            bad_codes = ["401", "404"]
            if (rid and sid) and sid not in bad_codes:
                log.info('Pre-binded %s' % self.jid.full())
                bosh_credentials = {
                    'BOSH_SERVICE': self.bosh,
                    'rid': int(rid),
                    'sid': sid,
                    'jid': self.jid.full(),
                }
                log.info('Succesfully prebinded %s' % self.jid)
            else:
                bosh_credentials = {
                    'unable_to_bind': True,
                }
                # if session code is 401 then we might have a case where plone
                # has the user in plone.registry however it is no longer
                # present on ejabbered
                # therefore we delete the user and password from xmpp and send
                # the bind_retry in order for prebind to be called again
                if rid == "401":
                    portal = getSite()
                    member_id = self.jid.user

                    pass_storage = queryUtility(IXMPPPasswordStorage,
                                                context=portal)
                    if pass_storage:
                            pass_storage.remove(member_id)
                    log.info("Reseting password for %s" % self.jid.user)
                if not self.request.get('retried'):
                    # Try one more time to bind users registered on login
                    bosh_credentials['bind_retry'] = True,
                log.warning('Unable to pre-bind %s' % self.jid)

        response = self.request.response
        response.setHeader('content-type', 'application/json')
        response.setHeader('Cache-Control',
                           'max-age=0, must-revalidate, private')
        response.setBody(json.dumps(bosh_credentials))
        return response
