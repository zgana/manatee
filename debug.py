# debug.py

import logging
import sys

LOGGER = logging.root

def LOG_F ():
    logging.debug ('called {0}()'.format (
        sys._getframe(1).f_code.co_name))

