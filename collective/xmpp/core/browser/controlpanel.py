# -*- coding: utf-8 -*-

from z3c.form import button
from z3c.form import form

from Products.statusmessages.interfaces import IStatusMessage
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from plone.app.registry.browser import controlpanel

from collective.xmpp.core.utils.setup import setupXMPPEnvironment
from collective.xmpp.core import messageFactory as _
from collective.xmpp.core.interfaces import IXMPPSettings 


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


class XMPPUserSetupForm(form.EditForm):
    """XMPP User Setup Form.
    """
    id = "XMPPUserSetupForm"
    label = _(u"XMPP User Setup")
    description = _("label_setup_warning",
        """
        WARNING: This action should ONLY be run after the initial setup. It
        will create the necessary users and nodes on your XMPP server
        according to your plone site users. Unless you know what you are doing
        you do not need to run it again afterwards.
        Make sure you have set the correct settings for you XMPP server before
        submitting.
        """)
    ignoreContext = True

    @button.buttonAndHandler(_('Register all users for XMPP'), name=None)
    def handleApply(self, action):
        data, errors = self.extractData()
        setupXMPPEnvironment(self.context)
        IStatusMessage(self.request).addStatusMessage(
                                    _(u"All users registered"), "info")
        self.context.REQUEST.RESPONSE.redirect("@@xmpp-settings")


class XMPPUserSetupControlPanel(controlpanel.ControlPanelFormWrapper):
    """XMPP user setup control panel.
    """
    form = XMPPUserSetupForm
    index = ViewPageTemplateFile('usersetup.pt')

