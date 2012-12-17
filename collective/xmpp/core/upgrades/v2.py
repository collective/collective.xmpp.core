
def updatePloneRegistry(context):
    context.runImportStepFromProfile('profile-collective.xmpp.core:default', 'plone.app.registry')
