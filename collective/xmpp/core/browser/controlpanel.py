# -*- coding: utf-8 -*-
import logging
from zope.component import queryUtility
from zope.component import getUtility
from z3c.form import button
from z3c.form import form
from z3c.form import field

from Products.statusmessages.interfaces import IStatusMessage
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.UserAndGroupSelectionWidget.z3cform.widget import \
                                            UsersAndGroupsSelectionWidgetFactory

from twisted.words.protocols.jabber.xmlstream import IQ
from wokkel.disco import NS_DISCO_ITEMS

from plone.registry.interfaces import IRegistry
from plone.app.registry.browser import controlpanel

from collective.xmpp.core import messageFactory as _
from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import IXMPPSettings 
from collective.xmpp.core.interfaces import IXMPPUserSetup
from collective.xmpp.core.utils import setup 
from collective.xmpp.core.utils import users
from collective.xmpp.core.interfaces import IXMPPUsers

log = logging.getLogger(__name__)


class XMPPSettingsEditForm(controlpanel.RegistryEditForm):
    """XMPP settings form.
    """
    schema = IXMPPSettings
    id = "XMPPSettingsEditForm"
    label = _(u"XMPP settings")

    @button.buttonAndHandler(_('Save'), name=None)
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self.applyChanges(data)
        IStatusMessage(self.request).addStatusMessage(_(u"Changes saved"),
                                                      "info")
        self.context.REQUEST.RESPONSE.redirect("@@xmpp-settings")

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        IStatusMessage(self.request).addStatusMessage(_(u"Edit cancelled"),
                                                      "info")
        self.request.response.redirect("%s/%s" % (self.context.absolute_url(),
                                                  self.control_panel_view))


class XMPPSettingsControlPanel(controlpanel.ControlPanelFormWrapper):
    """XMPP settings control panel.
    """
    form = XMPPSettingsEditForm
    index = ViewPageTemplateFile('xmppsettings.pt')


class XMPPUserSetupForm(form.Form):
    """XMPP User Setup Form.
    """
    ignoreContext = True
    id = "XMPPUserSetupForm"
    label = _(u"XMPP User Setup")
    description = _("label_setup_warning", """
        This page lets you register and deregister Plone users on the XMPP
        server. You can either choose specific users, or do it for all users in
        the site. Make sure you have set the correct settings for you XMPP 
        server before submitting.
        """)
    fields = field.Fields(IXMPPUserSetup)
    fields['users'].widgetFactory = UsersAndGroupsSelectionWidgetFactory

    def update(self):
        super(XMPPUserSetupForm, self).update()
        status = IStatusMessage(self.request)
        if self.request.form.get('form.widgets.register_all'):
            member_ids = users.getAllMemberIds() 
            setup.registerXMPPUsers(self.context, member_ids)
            status.add(_(u"All users were registered"), "info")

        elif self.request.form.get('form.widgets.deregister_all'):
            registry = getUtility(IRegistry)
            settings = registry.forInterface(IXMPPSettings, check=False)

            client = queryUtility(IAdminClient)
            if client is None:
                status.add(_(u"The XMPP Twisted utility could not be "
                "found. Either your XMPP settings are incorrect, or the Zope "
                "server was just restarted and the utility not yet registered "
                "again (it's registered upon page load). If it's the "
                "second case, please try again. Otherwise, check your XMPP "
                "settings."), "error")
                return
                
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
                        setup.deregisterXMPPUsers(self.context, member_jids)
                return result

            d = client.admin.getRegisteredUsers()
            d.addCallbacks(resultReceived)
            status.add(_(u"The XMPP users is being instructed to deregister all "
                        u"the users. This might take some minutes to complete."), "info")

        elif self.request.form.get('form.widgets.register_selected'):
            member_ids = self.request.form.get('form.widgets.users')
            setup.registerXMPPUsers(self.context, member_ids)
            status.add(_(u"The selected users where registered"), "info")

        elif self.request.form.get('form.widgets.deregister_selected'):
            member_jids = []
            member_ids = self.request.form.get('form.widgets.users')
            xmpp_users = getUtility(IXMPPUsers)
            for member_id in member_ids:
                member_jid = xmpp_users.getUserJID(member_id)
                member_jids.append(member_jid)

            setup.deregisterXMPPUsers(self.context, member_jids)
            status.add(_(u"The selected users were deregistered"), "info")


class XMPPUserSetupControlPanel(controlpanel.ControlPanelFormWrapper):
    """XMPP user setup control panel.
    """
    form = XMPPUserSetupForm
    index = ViewPageTemplateFile('usersetup.pt')
