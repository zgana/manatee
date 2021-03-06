# manateeimport.py


from __future__ import division, print_function

__doc__ = """Import entries."""


import datetime
import csv
import re


class TimeRecordingImporter (object):

    """Import from TimeRecording (Andriod App)."""

    def __init__ (self, filename, log, default=None):
        self.filename = filename
        self.log = log
        self.default = default
        with open (self.filename, 'rt') as f:
            self.lines = f.readlines ()

    def do_import (self):
        n_imported = 0
        for activity in sorted (self.log.timing_activities):
            n_imported += self.put_entries (activity.name)
        return n_imported

    def put_entries (self, activity_name):

        def get_line_info (line):
            return month, day, year, \
                    start_hour, start_minute, end_hour, end_minute, task

        n_imported = 0

        for line in self.lines:
            regex = '(\d\d)/(\d\d)/(\d\d\d\d),\w\w\w,'\
                    '(\d\d):(\d\d)( am| pm)?,(\d\d):(\d\d)( am| pm)?,' \
                    '\d\d:\d\d,([^,]*),(([^,]*),)?.*'
            m = re.match (regex, line)
            if not m:
                continue
            task = m.group (10)
            if re.match ('\d\d\.\d\d', task):
                task = m.group (12)
            task_match = re.match (activity_name, task)
            if not task_match:
                if not (activity_name == self.default and task == ''):
                    continue
            month = int (m.group (1))
            day = int (m.group (2))
            year = int (m.group (3))
            start_hour = int (m.group (4))
            start_minute = int (m.group (5))
            start_ampm = m.group (6)
            if start_ampm == ' pm':
                start_hour += 12
                start_hour %= 24;
            end_hour = int (m.group (7))
            end_minute = int (m.group (8))
            end_ampm = m.group (9)
            if end_ampm == ' pm':
                end_hour += 12
                end_hour %= 24;
            start_time = datetime.datetime (
                    year, month, day, start_hour, start_minute)
            end_time = datetime.datetime (
                    year, month, day, end_hour, end_minute)
            if start_time > end_time:
                end_time += datetime.timedelta (days=1)

            existing = self.log.get_entries (activity_name)
            try:
                for entry in existing:
                    overlap = entry.overlap_in_hours (start_time, end_time)
                    assert overlap == 0
            except:
                continue
            self.log.create_entry (activity_name, start_time, end_time)
            n_imported += 1

        return n_imported
