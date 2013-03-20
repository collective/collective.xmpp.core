from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from collective.xmpp.core.client import randomResource
from collective.xmpp.core.httpb import BOSHClient
from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import IXMPPSettings
from collective.xmpp.core.interfaces import IXMPPUsers
from collective.xmpp.core.utils import setup
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
import json
import logging

logger = logging.getLogger(__name__)


class XMPPLoader(BrowserView):
    """ """
    bind_retry = False

    def autoRegister(self, client):
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IXMPPSettings, check=False)
        if not settings.auto_register_on_login:
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
        if b_client.startSession():
            return b_client.rid, b_client.sid
        return ('', '')

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
            if rid and sid:
                logger.info('Pre-binded %s' % self.jid.full())
                bosh_credentials = {
                    'BOSH_SERVICE': self.bosh,
                    'rid': int(rid),
                    'sid': sid,
                    'jid': self.jid.full(),
                }
            else:
                bosh_credentials = {
                    'unable_to_bind': True,
                }
                logger.warning('Unable to pre-bind %s' % self.jid)

        response = self.request.response
        response.setHeader('content-type', 'application/json')
        response.setHeader('Cache-Control',
                           'max-age=0, must-revalidate, private')
        response.setBody(json.dumps(bosh_credentials))
        return response

