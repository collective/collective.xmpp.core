import string
import random
import logging
from BTrees.OOBTree import OOBTree
from persistent import Persistent
from zope.interface import implements
from collective.xmpp.core.interfaces import IXMPPPasswordStorage

logger = logging.getLogger(__name__)
chars = string.letters + string.digits

class XMPPPasswordStorage(Persistent):
    implements(IXMPPPasswordStorage)

    def __init__(self):
        self._passwords = OOBTree()

    def get(self, user_id):
        if user_id in self._passwords:
            return self._passwords[user_id]
        return None

    def set(self, user_id):
        password = ''.join([random.choice(chars) for i in range(12)])
        self._passwords[user_id] = password
        return password

    def remove(self, user_id):
        if user_id in self._passwords:
            del self._passwords[user_id]

    def clear(self):
        self._passwords.clear()
        logger.warning("The password storage has been wiped.")


