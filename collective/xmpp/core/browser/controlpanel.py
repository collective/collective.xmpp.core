# -*- coding: utf-8 -*-
from twisted.words.protocols.jabber.xmlstream import IQ
from wokkel.disco import NS_DISCO_ITEMS

from zope.component.hooks import getSite
from zope.component import queryUtility
from zope.component import getUtility

from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.interfaces import NO_VALUE

from Products.statusmessages.interfaces import IStatusMessage
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName

from plone.registry.interfaces import IRegistry
from plone.app.registry.browser import controlpanel

from collective.xmpp.core import messageFactory as _
from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import IXMPPPasswordStorage
from collective.xmpp.core.interfaces import IXMPPSettings
from collective.xmpp.core.interfaces import IXMPPUserSetup
from collective.xmpp.core.utils import setup
from collective.xmpp.core.utils import users
from collective.xmpp.core.decorators import newzodbconnection

UserAndGroupSelectionWidget_installed = True
try:
    # We have installed UserAndGroupSelectionWidget with version greated then 2.0.4
    from Products.UserAndGroupSelectionWidget.z3cform.widget import \
        UsersAndGroupsSelectionWidgetFactory
except ImportError:
    # UserAndGroupSelectionWidget > 2.0.4 not found
    UserAndGroupSelectionWidget_installed = False


class XMPPSettingsEditForm(controlpanel.RegistryEditForm):
    """ XMPP settings form.
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
    """ XMPP settings control panel.
    """
    form = XMPPSettingsEditForm
    index = ViewPageTemplateFile('xmppsettings.pt')


class XMPPUserSetupForm(form.Form):
    """ XMPP User Setup Form.
    """
    ignoreContext = True
    id = "XMPPUserSetupForm"
    label = _(u"XMPP User Setup")
    description = _("help_xmpp_user_setup", """
        This page lets you register and deregister Plone users on the XMPP
        server. You can either choose specific users, or do it for all users in
        the site. Make sure you have set the correct settings for you XMPP
        server before submitting.
        """)
    fields = field.Fields(IXMPPUserSetup)

    if UserAndGroupSelectionWidget_installed:
        fields['users'].widgetFactory = UsersAndGroupsSelectionWidgetFactory

    def update(self):
        super(XMPPUserSetupForm, self).update()
        if self.request.form.get('form.widgets.register_all'):
            return self.registerAll()
        elif self.request.form.get('form.widgets.deregister_all'):
            return self.deregisterAll()
        elif self.request.form.get('form.widgets.register_selected'):
            return self.registerSelected()
        elif self.request.form.get('form.widgets.deregister_selected'):
            return self.deregisterSelected()
        elif self.request.form.get('form.widgets.clear_all_passwords'):
            return self.clearAllPasswords()


    def registerAll(self):
        member_ids = users.getAllMemberIds()
        setup.registerXMPPUsers(self.context, member_ids)
        IStatusMessage(self.request).add(_(u"All users are being registered "
            "in the background. "
            "This might take a few minutes and your site might become "
            "unresponsive."), "info")

    def deregisterAll(self):
        portal = self.context
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IXMPPSettings, check=False)
        status = IStatusMessage(self.request)
        client = queryUtility(IAdminClient)
        if client is None:
            status.add(_(u"The XMPP Twisted utility could not be "
            "found. Either your XMPP settings are incorrect, or the Zope "
            "server was just restarted and the utility not yet registered "
            "again (it's registered upon page load). If it's the "
            "second case, please try again. Otherwise, check your XMPP "
            "settings."), "error")
            return

        @newzodbconnection
        def resultReceived(result):
            items = [item.attributes for item in result.query.children]
            if items[0].has_key('node'):
                for item in reversed(items):
                    iq = IQ(client.admin.xmlstream, 'get')
                    iq['to'] = settings.xmpp_domain
                    query = iq.addElement((NS_DISCO_ITEMS, 'query'))
                    query['node'] = item['node']
                    iq.send().addCallbacks(resultReceived)
            else:
                member_jids = [item['jid'] for item in items]
                if settings.admin_jid in member_jids:
                    member_jids.remove(settings.admin_jid)
                member_ids = [item.split('@')[0] for item in member_jids]
                if member_ids:
                    portal = getSite()
                    setup.deregisterXMPPUsers(portal, member_ids)
            return result

        d = client.admin.getRegisteredUsers()
        d.addCallbacks(resultReceived)
        status.add(_(u"The XMPP server is being instructed to deregister all "
                    u"the users. This might take some minutes to complete."), "info")
        return d

    def getChosenMembers(self):
        """ The Products.UserAndGroupSelectionWidget can return users and groups.

            Identify the chosen groups and return their members as well as the
            individually chosen members (while removing duplicates).
        """
        members_and_groups = self.request.form.get('form.widgets.users')
        members = []

        if UserAndGroupSelectionWidget_installed:
            pg = getToolByName(self.context, 'portal_groups')
            groups = pg.getGroupIds()
            chosen_groups = list(set(members_and_groups).intersection(set(groups)))
            chosen_members = list(set(members_and_groups).difference(set(groups)))

            for g in chosen_groups:
                chosen_members += pg.getGroupById(g).getGroupMemberIds()

            members = list(set(chosen_members))
        else:
            # Case when Products.UserAndGroupSelectionWidget is not installed/used
            members = [member for member in members_and_groups.split('\r\n')
                           if member]
        return members

    def deregisterSelected(self):
        status = IStatusMessage(self.request)
        widget = self.widgets.get('users')
        if widget.extract() == NO_VALUE:
            status.add(_(u"You first need to choose the users to deregister"),
                        "error")
            return
        setup.deregisterXMPPUsers(self.context, self.getChosenMembers())
        return status.add(_(u"The selected users were deregistered"), "info")

    def registerSelected(self):
        status = IStatusMessage(self.request)
        widget = self.widgets.get('users')
        if widget.extract() == NO_VALUE:
            status.add(_(u"You first need to choose the users to register"),
                        "error")
            return
        setup.registerXMPPUsers(self.context, self.getChosenMembers())
        return status.add(_(u"The selected users where registered"), "info")

    def clearAllPasswords(self):
        status = IStatusMessage(self.request)
        pass_storage = getUtility(IXMPPPasswordStorage)
        pass_storage.clear()
        status.add(_(u"The password storage has been wiped."), "info")


class XMPPUserSetupControlPanel(controlpanel.ControlPanelFormWrapper):
    """ XMPP user setup control panel.
    """
    form = XMPPUserSetupForm
    index = ViewPageTemplateFile('usersetup.pt')
