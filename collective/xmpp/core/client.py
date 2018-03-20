import logging
import random
import string

log = logging.getLogger(__name__)


def randomResource():
    chars = string.letters + string.digits
    resource = 'auto-' + ''.join([random.choice(chars) for i in range(10)])
    return resource
