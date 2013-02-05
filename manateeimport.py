# manateeimport.py


from __future__ import division, print_function

__doc__ = """Import entries."""


import datetime as dt
import csv
import re


class TimeRecordingImporter (object):

    """Import from TimeRecording (Andriod App)."""

    def __init__ (self, filename):
        self.filename = filename
        with open (self.filename, 'rt') as f:
            self.lines = f.readlines ()

    def get_entries (self, activity_name, regex):
        pass
