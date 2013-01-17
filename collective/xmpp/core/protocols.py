import transaction
import string
import random
import logging
import Zope2
from twisted.words.protocols.jabber.jid import JID
from twisted.words.protocols.jabber.xmlstream import IQ
from twisted.words.xish.domish import Element
from wokkel import data_form
from wokkel.disco import NS_DISCO_INFO, NS_DISCO_ITEMS
from wokkel.pubsub import NS_PUBSUB_OWNER, NS_PUBSUB_NODE_CONFIG
from wokkel.pubsub import PubSubClient as WokkelPubSubClient
from wokkel.subprotocols import XMPPHandler

from zope.component.hooks import setSite
from Products.CMFCore.utils import getToolByName
from collective.xmpp.core.utils import users

NS_VCARD_TEMP = 'vcard-temp'
NS_CLIENT = 'jabber:client'
NS_ROSTER_X = 'http://jabber.org/protocol/rosterx'
NS_COMMANDS = 'http://jabber.org/protocol/commands'
NODE_ADMIN = 'http://jabber.org/protocol/admin'
NODE_ADMIN_GET_REGISTERED_USERS = NODE_ADMIN + '#get-registered-users-list'
NODE_ADMIN_ADD_USER = NODE_ADMIN + '#add-user'
NODE_ADMIN_DELETE_USER = NODE_ADMIN + '#delete-user'
NODE_ADMIN_ANNOUNCE = NODE_ADMIN + '#announce'
XHTML_IM = 'http://jabber.org/protocol/xhtml-im'
XHTML = 'http://www.w3.org/1999/xhtml'

ADMIN_REQUEST = "/iq[@type='get' or @type='set']" \
                "/command[@xmlns='%s' and @node='/%s']" % \
                (NS_COMMANDS, NODE_ADMIN)

log = logging.getLogger(__name__)


def getRandomId():
    chars = string.letters + string.digits
    return ''.join([random.choice(chars) for i in range(10)])


class ChatHandler(XMPPHandler):
    """ Simple chat client.
        http://xmpp.org/extensions/xep-0071.html
    """

    def sendMessage(self, to, body):
        """ Send a text message
        """
        message = Element((None, "message", ))
        message["id"] = getRandomId()
        message["from"] = self.xmlstream.factory.authenticator.jid.full()
        message["to"] = to.full()
        message["type"] = 'chat'
        message.addElement('body', content=body)
        self.xmlstream.send(message)
        return True

    def sendXHTMLMessage(self, to, body, xhtml_body):
        """ Send an HTML message.
        """
        message = Element((NS_CLIENT, "message", ))
        message["id"] = getRandomId()
        message["from"] = self.xmlstream.factory.authenticator.jid.full()
        message["to"] = to.full()
        message["type"] = 'chat'
        message.addElement('body', content=body)
        html = message.addElement((XHTML_IM, 'html'))
        html_body = html.addElement((XHTML, 'body'))
        html_body.addRawXml(xhtml_body)
        self.xmlstream.send(message)
        return True

    def sendRosterItemAddSuggestion(self, to, items, portal, group=None):
        """ Suggest a user(s) to be added in the roster.
        """
        app = Zope2.app()
        root = app.unrestrictedTraverse('/'.join(portal.getPhysicalPath()))
        setSite(root)
        transaction.begin()
        try:
            mt = getToolByName(root, 'portal_membership', None)
            message = Element((None, "message", ))
            message["id"] = getRandomId()
            message["from"] = self.xmlstream.factory.authenticator.jid.full()
            message["to"] = to.userhost()
            x = message.addElement((NS_ROSTER_X, 'x'))
            for jid in items:
                if to == jid:
                    continue

                member_id = users.unescapeNode(jid.user)
                if mt is not None and mt.getMemberInfo(member_id):
                    info = mt.getMemberInfo(member_id)
                    fullname = info.get('fullname', member_id).decode('utf-8')
                else:
                    log.warn('Could not get user fullname')
                    fullname = ''

                item = x.addElement('item')
                item["action"]='add'
                item["jid"] = jid.userhost()
                item["name"] = fullname
                if group:
                    item.addElement('group', content=group)
            self.xmlstream.send(message)
            transaction.commit()
        except Exception, e:
            log.error(e)
            transaction.abort()
        finally:
            setSite(None)
            app._p_jar.close()
        return True


class VCardHandler(XMPPHandler):
    """ """

    def createVCardIQ(self, udict):
        """ <FN>Jeremie Miller</FN>
            <NICKNAME>jer</NICKNAME>
            <EMAIL><INTERNET/><PREF/><USERID>jeremie@jabber.org</USERID></EMAIL>
            <JABBERID>jer@jabber.org</JABBERID>
        """
        iq = IQ(self.xmlstream, 'set')
        vcard = iq.addElement((NS_VCARD_TEMP, 'vCard'))
        vcard['version'] = '3.0'
        fn = vcard.addElement('FN', content=udict.get('fullname'))
        vcard.addElement('NICKNAME', content=udict.get('nickname'))
        email = vcard.addElement('EMAIL')
        email.addElement('INTERNET')
        email.addElement('PREF')
        email.addElement('USERID', content=udict.get('userid'))
        vcard.addElement('JABBERID', content=udict.get('jabberid'))
        return iq

    def sendVCard(self):
        def resultReceived(iq):
            log.info("Result received for vcard set")
            return True

        def error(failure):
            log.error(failure.getTraceback())
            return False

        iq = self.createVCardIQ()
        d = iq.send()
        d.addCallbacks(resultReceived, error)


class AdminHandler(XMPPHandler):
    """ Admin client.
        http://xmpp.org/extensions/xep-0133.html
    """

    def getRegisteredUsers(self):
        """ XXX: This is ejabberd specific. ejabberd does not implement
        the #get-registered-users-list command, instead does it with an iq/get.
        """
        iq = IQ(self.xmlstream, 'get')
        iq['to'] = users.getXMPPDomain() 
        query = iq.addElement((NS_DISCO_ITEMS, 'query'))
        query['node'] = 'all users'
        d = iq.send()
        return d

    def addUser(self, userjid, password):
        """ Add a user
        """

        def resultReceived(iq):
            log.info("Added user %s %s" % (userjid, password))
            return True

        def formReceived(iq):
            command = iq.command
            sessionid = command['sessionid']
            form = data_form.findForm(command, NODE_ADMIN)

            response = IQ(self.xmlstream, 'set')
            response['to'] = iq['from']
            response['id'] = iq['id']

            command = response.addElement((NS_COMMANDS, 'command'))
            command['node'] = NODE_ADMIN_ADD_USER
            command['sessionid'] = sessionid

            form.formType = 'submit'
            form.fields['accountjid'].value = userjid
            form.fields['password'].value = password
            form.fields['password-verify'].value = password

            command.addChild(form.toElement())
            d = response.send()
            d.addCallbacks(resultReceived, error)
            return d

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return False

        iq = IQ(self.xmlstream, 'set')
        iq['to'] = users.getXMPPDomain() 
        command = iq.addElement((NS_COMMANDS, 'command'))
        command['action'] = 'execute'
        command['node'] = NODE_ADMIN_ADD_USER
        d = iq.send()
        d.addCallbacks(formReceived, error)
        return d

    def deleteUsers(self, userjids):
        """ """

        def resultReceived(iq):
            log.info("Deleted users %s" % userjids)
            return True

        def formReceived(iq):
            command = iq.command
            sessionid = command['sessionid']
            form = data_form.findForm(command, NODE_ADMIN)

            response = IQ(self.xmlstream, 'set')
            response['to'] = iq['from']
            response['id'] = iq['id']

            command = response.addElement((NS_COMMANDS, 'command'))
            command['node'] = NODE_ADMIN_DELETE_USER
            command['sessionid'] = sessionid

            form.formType = 'submit'
            form.fields['accountjids'].values = userjids

            command.addChild(form.toElement())
            d = response.send()
            d.addCallbacks(resultReceived, error)
            return d

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return False

        if isinstance(userjids, basestring):
            userjids = [userjids]
        iq = IQ(self.xmlstream, 'set')
        iq['to'] = users.getXMPPDomain()
        command = iq.addElement((NS_COMMANDS, 'command'))
        command['action'] = 'execute'
        command['node'] = NODE_ADMIN_DELETE_USER
        d = iq.send()
        d.addCallbacks(formReceived, error)
        return d

    def sendAnnouncement(self, body, subject='Announce'):
        """ Send an announement to all users.
        """

        def resultReceived(iq):
            log.info("Sent announcement %s." % body)
            return True

        def formReceived(iq):
            command = iq.command
            sessionid = command['sessionid']
            form = data_form.findForm(command, NODE_ADMIN)

            #from twisted.words.protocols.jabber.xmlstream import toResponse
            #response = toResponse(iq, 'set')
            response = IQ(self.xmlstream, 'set')
            response['to'] = iq['from']
            response['id'] = iq['id']

            command = response.addElement((NS_COMMANDS, 'command'))
            command['node'] = NODE_ADMIN_ANNOUNCE
            command['sessionid'] = sessionid

            form.formType = 'submit'
            form.fields['subject'].value = subject
            form.fields['body'].value = body

            command.addChild(form.toElement())
            d = response.send()
            d.addCallbacks(resultReceived, error)
            return d

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return False

        iq = IQ(self.xmlstream, 'set')
        iq['to'] = users.getXMPPDomain() 
        command = iq.addElement((NS_COMMANDS, 'command'))
        command['action'] = 'execute'
        command['node'] = NODE_ADMIN_ANNOUNCE
        d = iq.send()
        d.addCallbacks(formReceived, error)
        return d


class PubSubHandler(WokkelPubSubClient):
    """ Pubslish-Subscribe
        http://xmpp.org/extensions/xep-0060.html
        http://xmpp.org/extensions/xep-0248.html
    """

    def publish(self, service, nodeIdentifier, items=[]):

        def cb(result):
            log.info("Published to node %s." % nodeIdentifier)
            return True

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return False


        d = super(PubSubHandler, self).publish(service, nodeIdentifier, items)
        d.addCallbacks(cb, error)
        return d

    def itemsReceived(self, event):
        log.info("Items received. %s." % event.items)
        if hasattr(self.parent, 'itemsReceived'):
            self.parent.itemsReceived(event)

    def createNode(self, service, nodeIdentifier, options=None):

        def cb(result):
            log.info("Created node %s." % nodeIdentifier)
            return True

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return False
        d = super(PubSubHandler, self).createNode(
            service,
            nodeIdentifier=nodeIdentifier,
            options=options)
        d.addCallbacks(cb, error)
        return d

    def deleteNode(self, service, nodeIdentifier):

        def cb(result):
            log.info("Deleted node %s." % nodeIdentifier)
            return True

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return False

        d = super(PubSubHandler, self).deleteNode(service, nodeIdentifier)
        d.addCallbacks(cb, error)
        return d

    def getNodes(self, service, nodeIdentifier=None):

        def cb(result):
            items = result.query.children
            result = [item.attributes for item in items]
            log.info("Got nodes of %s: %s ." % (nodeIdentifier, result))
            return result

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return []

        iq = IQ(self.xmlstream, 'get')
        iq['to'] = service.full()
        query = iq.addElement((NS_DISCO_ITEMS, 'query'))
        if nodeIdentifier is not None:
            query['node'] = nodeIdentifier
        d = iq.send()
        d.addCallbacks(cb, error)
        return d

    def getSubscriptions(self, service, nodeIdentifier):

        def cb(result):
            subscriptions = result.pubsub.subscriptions.children
            result = [(JID(item['jid']), item['subscription'])
                     for item in subscriptions]
            log.info("Got subscriptions for %s: %s ." % \
                (nodeIdentifier, result))
            return result

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return []

        iq = IQ(self.xmlstream, 'get')
        iq['to'] = service.full()
        pubsub = iq.addElement((NS_PUBSUB_OWNER, 'pubsub'))
        subscriptions = pubsub.addElement('subscriptions')
        subscriptions['node'] = nodeIdentifier
        d = iq.send()
        d.addCallbacks(cb, error)
        return d

    def setSubscriptions(self, service, nodeIdentifier, delta):

        def cb(result):
            if result['type']==u'result':
                log.info("Set subscriptions for %s: %s ." % \
                    (nodeIdentifier, delta))
                return True
            return False

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return False

        iq = IQ(self.xmlstream, 'set')
        iq['to'] = service.full()
        pubsub = iq.addElement((NS_PUBSUB_OWNER, 'pubsub'))
        subscriptions = pubsub.addElement('subscriptions')
        subscriptions['node']=nodeIdentifier
        for jid, subscription in delta:
            el = subscriptions.addElement('subscription')
            el['jid'] = jid.userhost()
            el['subscription'] = subscription

        d = iq.send()
        d.addCallbacks(cb, error)
        return d

    def getNodeType(self, service, nodeIdentifier):

        def cb(result):
            result = result.query.identity['type']
            log.info("Got node type %s: %s ." % (nodeIdentifier, result))
            return result

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return []

        iq = IQ(self.xmlstream, 'get')
        iq['to'] = service.full()
        query = iq.addElement((NS_DISCO_INFO, 'query'))
        query['node'] = nodeIdentifier
        d = iq.send()
        d.addCallbacks(cb, error)
        return d

    def getDefaultNodeConfiguration(self, service):

        def cb(result):
            fields = [field
                      for field in result.pubsub.default.x.children
                      if field[u'type']!=u'hidden']
            result = dict()
            for field in fields:
                value = None
                try:
                    value = field.value.children[0]
                except (AttributeError, IndexError):
                    pass
                result[field['var']] = value
            log.info("Got default node configuration: %s ." % result)
            return result

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return []

        iq = IQ(self.xmlstream, 'get')
        iq['to'] = service.full()
        pubsub = iq.addElement((NS_PUBSUB_OWNER, 'pubsub'))
        pubsub.addElement('default')
        d = iq.send()
        d.addCallbacks(cb, error)
        return d

    def getNodeConfiguration(self, service, nodeIdentifier):

        def cb(result):
            fields = [field
                      for field in result.pubsub.configure.x.children
                      if field[u'type']!=u'hidden']
            result = dict()
            for field in fields:
                value = None
                try:
                    value = field.value.children[0]
                except (AttributeError, IndexError):
                    pass
                result[field['var']] = value
            log.info("Got node config  %s: %s ." % (nodeIdentifier, result))
            return result

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return []

        iq = IQ(self.xmlstream, 'get')
        iq['to'] = service.full()
        pubsub = iq.addElement((NS_PUBSUB_OWNER, 'pubsub'))
        configure = pubsub.addElement('configure')
        configure['node'] = nodeIdentifier
        d = iq.send()
        d.addCallbacks(cb, error)
        return d

    def configureNode(self, service, nodeIdentifier, options):

        def cb(result):
            log.info("Configured %s: %s ." % (nodeIdentifier, options))
            return True

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return False

        form = data_form.Form(formType='submit',
                              formNamespace=NS_PUBSUB_NODE_CONFIG)
        form.makeFields(options)
        iq = IQ(self.xmlstream, 'set')
        iq['to'] = service.full()
        pubsub = iq.addElement((NS_PUBSUB_OWNER, 'pubsub'))
        configure = pubsub.addElement('configure')
        configure['node'] = nodeIdentifier
        configure = configure.addChild(form.toElement())
        d = iq.send()
        d.addCallbacks(cb, error)
        return d

    def associateNodeWithCollection(self, service,
                                    nodeIdentifier, collectionIdentifier):
        """ XXX: Not supported by ejabberd
        """

        def cb(result):
            return True

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return False

        iq = IQ(self.xmlstream, 'set')
        iq['to'] = service.full()
        pubsub = iq.addElement((NS_PUBSUB_OWNER, 'pubsub'))
        collection = pubsub.addElement('collection')
        collection['node'] = collectionIdentifier
        associate = collection.addElement('associate')
        associate['node'] = nodeIdentifier
        d = iq.send()
        d.addCallbacks(cb, error)
        return d

    def getAffiliations(self, service, nodeIdentifier):

        def cb(result):
            affiliations = result.pubsub.affiliations
            result = []
            for affiliate in affiliations.children:
                result.append((JID(affiliate['jid']),
                               affiliate['affiliation'], ))
            log.info("Got affiliations for %s: %s ." % \
                (nodeIdentifier, result))
            return result

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return []

        iq = IQ(self.xmlstream, 'get')
        iq['to'] = service.full()
        pubsub = iq.addElement((NS_PUBSUB_OWNER, 'pubsub'))
        affiliations = pubsub.addElement('affiliations')
        affiliations['node']=nodeIdentifier
        d = iq.send()
        d.addCallbacks(cb, error)
        return d

    def modifyAffiliations(self, service, nodeIdentifier, delta):

        def cb(result):
            if result['type']==u'result':
                log.info("Modified affiliations for %s: %s ." % \
                    (nodeIdentifier, delta))
                return True
            return False

        def error(failure):
            # TODO: Handle gracefully?
            log.error(failure.getTraceback())
            return False

        iq = IQ(self.xmlstream, 'set')
        iq['to'] = service.full()
        pubsub = iq.addElement((NS_PUBSUB_OWNER, 'pubsub'))
        affiliations = pubsub.addElement('affiliations')
        affiliations['node']=nodeIdentifier
        for jid, affiliation in delta:
            el = affiliations.addElement('affiliation')
            el['jid'] = jid.userhost()
            el['affiliation'] = affiliation

        d = iq.send()
        d.addCallbacks(cb, error)
        return d
