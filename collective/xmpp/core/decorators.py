import Zope2
import logging
import transaction
from zope.component.hooks import setSite
from zope.component.hooks import getSite

log = logging.getLogger(__name__)


def newzodbconnection(f, *args, **kw):
    """ In callback methods, we don't have an open ZODB connection, so we
        have to create one.

        If you get "ZODB.Connection Couldn't load state for xxx" errors, then
        you need this decorator.

        WARNING: this decorator discards the previous connection and loads a
        new one. Methods with this decorator must therefore allways  be called 
        in a separate thread.
    """
    portal = getSite()
    def wrapper(*args, **kw):
        result = None
        setSite(None)
        app = Zope2.app()
        root = app.unrestrictedTraverse('/'.join(portal.getPhysicalPath()))
        setSite(root)
        transaction.begin()
        try:
            result = f(*args, **kw)
            transaction.commit()
        except Exception, e:
            log.error(e)
            transaction.abort()
        finally:
            setSite(None)
            app._p_jar.close()
        return result
    return wrapper 
