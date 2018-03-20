# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.FSImage import FSImage
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from collective.xmpp.core import messageFactory as _
from collective.xmpp.core.interfaces import IXMPPSettings
from collective.xmpp.core.interfaces import IXMPPUserSetup
from collective.xmpp.core.interfaces import IXMPPUsers
from collective.xmpp.core.utils import users
from plone.app.registry.browser import controlpanel
from plone.registry.interfaces import IRegistry
from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.interfaces import NO_VALUE
from zope.component import getUtility
import logging

log = logging.getLogger(__name__)
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

    def updateVCards(self, member_ids=[]):
        """ """
        portal = self.context
        registry = getUtility(IRegistry)
        settings = registry.forInterface(IXMPPSettings, check=False)
        status = IStatusMessage(self.request)
        portal_url = getToolByName(portal, 'portal_url')()
        member_dicts = []

        # XXX: This is a hack. We get vcard data for all users in the site,
        # without yet knowing whether they are actually registered in the
        # XMPP server. We do this here because getPersonalPortrait doesn't
        # work in callbacks (due to Request not being set up properly).
        xmpp_users = getUtility(IXMPPUsers)
        mtool = getToolByName(portal, 'portal_membership')
        member_ids = member_ids or users.getAllMemberIds()
        log.info('Total members are: %d' % len(member_ids))
        i = 0
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
            }
            member_dicts.append(udict)
            i += 1
            log.info('Fetched details for member %d, %s' % (i, fullname))

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


class XMPPUserSetupControlPanel(controlpanel.ControlPanelFormWrapper):
    """ XMPP user setup control panel.
    """
    form = XMPPUserSetupForm
    index = ViewPageTemplateFile('usersetup.pt')
