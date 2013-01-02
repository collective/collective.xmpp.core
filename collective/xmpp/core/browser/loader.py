import logging
import json
from zope.component import (
    getUtility,
    queryUtility,
    getSiteManager
)
from zope.component.hooks import getSite
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from twisted.words.protocols.jabber.jid import JID
from collective.xmpp.core.client import randomResource
from collective.xmpp.core.httpb import BOSHClient
from collective.xmpp.core.utils import setup
from collective.xmpp.core.interfaces import (
    IAdminClient,
    IXMPPUsers,
    IXMPPSettings
)
from collective.xmpp.core.utils.users import escapeNode

logger = logging.getLogger(__name__)

class XMPPLoader(BrowserView):
    """ """
    bind_retry = False

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

            # If not already registered, auto-register Plone users on login
            registry = getUtility(IRegistry)
            settings = registry.forInterface(IXMPPSettings, check=False)
            setup.registerXMPPUsers(getSite(), [self.user_id])

            if settings.auto_subscribe:
                self.member_jids = []
                self.bind_retry = True

                def getUserJID(user_id):
                    sm = getSiteManager(self.context)
                    registry = sm.getUtility(IRegistry)
                    settings = registry.forInterface(IXMPPSettings, check=False)
                    return JID("%s@%s" % (escapeNode(user_id), settings.xmpp_domain))

                def resultReceived(result):
                    items = [item.attributes for item in result.query.children]
                    if items[0].has_key('node'):
                        for item in reversed(items):
                            iq = IQ(client.admin.xmlstream, 'get')
                            iq['to'] = client.admin.xmlstream.factory.authenticator.jid.host
                            query = iq.addElement((NS_DISCO_ITEMS, 'query'))
                            query['node'] = item['node']
                            iq.send().addCallbacks(resultReceived)
                    else:
                        member_jids = [item['jid'] for item in items]
                        if settings.admin_jid in member_jids:
                            member_jids.remove(settings.admin_jid)
                        if member_jids:
                            self.member_jids.extend(member_jids)

                        client.chat.sendRosterItemAddSuggestion(
                            self.jid,
                            [getUserJID(user_id.split('@')[0])
                                    for user_id in self.member_jids
                                        if self.user_id != user_id.split('@')[0]],
                            self.context.portal_url.getPortalObject())
                    return result

                d = client.admin.getRegisteredUsers()
                d.addCallbacks(resultReceived)

            return

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
                logger.warning('Unable to pre-bind %s' % self.jid)

        response = self.request.response
        response.setHeader('content-type', 'application/json')
        response.setHeader('Cache-Control', 'max-age=0, must-revalidate, private')
        response.setBody(json.dumps(bosh_credentials))
        return response

