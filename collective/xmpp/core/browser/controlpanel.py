# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.FSImage import FSImage
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from collective.xmpp.core import messageFactory as _
from collective.xmpp.core.decorators import newzodbconnection
from collective.xmpp.core.exceptions import AdminClientNotConnected
from collective.xmpp.core.interfaces import IAdminClient
from collective.xmpp.core.interfaces import IXMPPPasswordStorage
from collective.xmpp.core.interfaces import IXMPPSettings
from collective.xmpp.core.interfaces import IXMPPUserSetup
from collective.xmpp.core.interfaces import IXMPPUsers
from collective.xmpp.core.interfaces import IZopeReactor
from collective.xmpp.core.utils import setup
from collective.xmpp.core.utils import users
from plone.app.registry.browser import controlpanel
from plone.registry.interfaces import IRegistry
from twisted.words.protocols.jabber.xmlstream import IQ
from wokkel.disco import NS_DISCO_ITEMS
from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.interfaces import NO_VALUE
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite

UserAndGroupSelectionWidget_installed = True
try:
    # We have installed UserAndGroupSelectionWidget with version greated
    # then 2.0.4
    from Products.UserAndGroupSelectionWidget.z3cform.widget import \
        UsersAndGroupsSelectionWidgetFactory
except ImportError:
    # UserAndGroupSelectionWidget > 2.0.4 not found
    UserAndGroupSelectionWidget_installed = False


UTILITY_NOT_FOUND_MESSAGE = _(
    u"The XMPP Twisted utility could not be "
    u"found. Either your XMPP settings are incorrect, or the Zope "
    u"server was just restarted and the utility not yet "
    u"registered again (it's registered upon page load). If "
    u"it's the second case, please try again. Otherwise, check "
    u"your XMPP settings.")


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
        elif self.request.form.get('form.widgets.update_vcards'):
            return self.updateVCards()
        elif self.request.form.get('form.widgets.update_selected_vcards'):
            return self.updateSelectedVCards()
        elif self.request.form.get('form.widgets.register_selected'):
            return self.registerSelected()
        elif self.request.form.get('form.widgets.deregister_selected'):
            return self.deregisterSelected()
        elif self.request.form.get('form.widgets.clear_all_passwords'):
            return self.clearAllPasswords()

    def registerAll(self):
        status = IStatusMessage(self.request)
        member_ids = users.getAllMemberIds()
        try:
            setup.registerXMPPUsers(self.context, member_ids)
        except AdminClientNotConnected:
            status.add(
                _(u"We are not yet connected to the XMPP "
                  u"server. Either your settings are incorrect, or "
                  u"you're trying to register users immediately after the "
                  u"ZServer has been restarted. If your settings are correct, "
                  u"then try again, it should work now. "), "warn")
            return
        status.add(_(
            u"All users are being registered in the background. "
            "This might take a few minutes and your site might become "
            "unresponsive."), "info")

    def deregisterAll(self):
        portal = self.context
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IXMPPSettings, check=False)
        status = IStatusMessage(self.request)
        client = queryUtility(IAdminClient)
        if client is None:
            status.add(UTILITY_NOT_FOUND_MESSAGE, "error")
            return

        @newzodbconnection(portal=portal)
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
                     u"the users. This might take some minutes to complete."),
                   "info")
        return d

    def updateVCards(self, member_ids=[]):
        """ """
        portal = self.context
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IXMPPSettings, check=False)
        status = IStatusMessage(self.request)
        client = queryUtility(IAdminClient)
        portal_url = getToolByName(portal, 'portal_url')()
        member_dicts = []
        pass_storage = getUtility(IXMPPPasswordStorage)
        if client is None:
            status.add(UTILITY_NOT_FOUND_MESSAGE, "error")
            return

        # XXX: This is a hack. We get vcard data for all users in the site,
        # without yet knowing whether they are actually registered in the
        # XMPP server. We do this here because getPersonalPortrait doesn't
        # work in callbacks (due to Request not being set up properly).
        xmpp_users = getUtility(IXMPPUsers)
        mtool = getToolByName(portal, 'portal_membership')
        member_ids = member_ids or users.getAllMemberIds()
        for member_id in member_ids:
            member = mtool.getMemberById(member_id)
            fullname = member.getProperty('fullname').decode('utf-8')
            user_jid = xmpp_users.getUserJID(member_id)
            portrait = mtool.getPersonalPortrait(member_id)
            if isinstance(portrait, FSImage):
                raw_image = portrait._data
            else:
                raw_image = portrait.data
            udict = {
                'fullname': fullname,
                'nickname': member_id,
                'email': member.getProperty('email'),
                'userid': user_jid.userhost(),
                'jabberid': user_jid.userhost(),
                'url': '%s/author/%s' % (portal_url, member_id),
                'image_type': portrait.content_type,
                'raw_image': raw_image,
                'jid_obj': user_jid,
                'pass': pass_storage.get(member_id)
            }
            member_dicts.append(udict)

        @newzodbconnection(portal=portal)
        def resultReceived(result):
            items = [item.attributes for item in result.query.children]
            if 'node' in items[0]:
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
                registered_member_dicts = \
                    [d for d in member_dicts if d['jabberid'] in member_jids]

                @newzodbconnection(portal=portal)
                def updateVCard():
                    mdict = registered_member_dicts.pop()
                    setup.setVCard(
                        mdict,
                        mdict['jid_obj'],
                        mdict['pass'],
                        updateVCard)

                if len(registered_member_dicts):
                    zr = getUtility(IZopeReactor)
                    zr.reactor.callInThread(updateVCard)
            return

        d = client.admin.getRegisteredUsers()
        d.addCallbacks(resultReceived)
        status.add(_(u"Each XMPP-registered user is having their vCard "
                     u"updated. This might take some minutes to complete."),
                   "info")
        return d

    def getChosenMembers(self):
        """ The Products.UserAndGroupSelectionWidget can return users and
            groups.

            Identify the chosen groups and return their members as well as the
            individually chosen members (while removing duplicates).
        """
        members_and_groups = self.request.form.get('form.widgets.users')
        members = []

        if UserAndGroupSelectionWidget_installed:
            pg = getToolByName(self.context, 'portal_groups')
            groups = pg.getGroupIds()
            chosen_groups = \
                list(set(members_and_groups).intersection(set(groups)))
            chosen_members = \
                list(set(members_and_groups).difference(set(groups)))

            for g in chosen_groups:
                chosen_members += pg.getGroupById(g).getGroupMemberIds()

            members = list(set(chosen_members))
        else:
            # Case when Products.UserAndGroupSelectionWidget is not
            # installed/used
            members = [member for member in members_and_groups.split('\r\n')
                       if member]
        return members

    def updateSelectedVCards(self):
        status = IStatusMessage(self.request)
        widget = self.widgets.get('users')
        if widget.extract() == NO_VALUE:
            status.add(_(u"You first need to choose the users"), "error")
            return
        self.updateVCards(member_ids=self.getChosenMembers())
        return status.add(_(u"The selected users' vCards are being updated in "
                            u"the background."), "info")

    def deregisterSelected(self):
        status = IStatusMessage(self.request)
        widget = self.widgets.get('users')
        if widget.extract() == NO_VALUE:
            status.add(_(u"You first need to choose the users to deregister"),
                       "error")
            return
        setup.deregisterXMPPUsers(self.context, self.getChosenMembers())
        return status.add(_(u"The selected users are being deregistered in "
                            u"the background."), "info")

    def registerSelected(self):
        status = IStatusMessage(self.request)
        widget = self.widgets.get('users')
        if widget.extract() == NO_VALUE:
            status.add(_(u"You first need to choose the users to register"),
                       "error")
            return
        try:
            setup.registerXMPPUsers(self.context, self.getChosenMembers())
        except AdminClientNotConnected:
            status.add(
                _(u"We are not yet connected to the XMPP "
                  u"server. Either your settings are incorrect, or "
                  u"you're trying to register users immediately after the "
                  u"ZServer has been restarted. If your settings are correct, "
                  u"then try again, it should work now. "), "warn")
            return
        return status.add(_(u"The selected users are being registered "
                            u"in the background."), "info")

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
