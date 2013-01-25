# manateelog.py


from __future__ import division, print_function

__doc__ = """Log daily activities."""

import datetime
from itertools import izip
import re

def timedelta_to_seconds (dt):
    """Return the number of seconds a timedelta lasts as a float."""
    return dt.seconds + dt.microseconds / 1E6 + dt.days * 86400

class CountingActivity (object):

    """Something someone might do any given day."""

    def __init__ (self, name, unit='none'):
        """Construct a CountingActivity.

        :type   name: str
        :param  name: The name of the CountingActivity.

        :type   unit: str
        :param  unit: The unit in which this CountingActivity is measured.
        """
        self.name = name
        self.unit = unit

    def __repr__ (self):
        return 'CountingActivity(name="{0}", unit="{1}")'.format (
                self.name, self.unit)

    def change_units (self, entries, new_unit, factor):
        """Change the unit of the CountingActivity.

        :type   new_unit: str
        :param  new_unit: The name of the new unit.

        :type   factor: float
        :param  factor: The number of [new_unit] equal to 1 [old_unit].
        """
        for entry in entries:
            entry.n *= factor
            entry.error *= factor
        self.unit = new_unit

    @property
    def kind (self):
        return 'counting'

    def __cmp__ (a, b):
        return cmp (a.name, b.name)

class TimingActivity (object):

    """Something one time-tracks."""

    def __init__ (self, name):
        """Construct a TimingActivity."""
        self.name = name

    def __repr__ (self):
        return 'TimingActivity(name="{0}")'.format (self.name)

    @property
    def kind (self):
        return 'timing'

    def __cmp__ (a, b):
        return cmp (a.name, b.name)

class CountingEntry (object):

    """An entry in the Log."""

    def __init__ (self, activity, date, n, error=0, note=''):
        """Construct a CountingEntry.
        
        :type   activity: :class:`Activity`
        :param  activity: The Activity this CountingEntry relates to.

        :type   date: datetime.date
        :param  date: The date this CountingEntry relates to.

        :type   n: float
        :param  n: The quantity associated with this CountingEntry.

        :type   error: float
        :param  error: Error estimate for n.

        :type   note: str
        :param  note: An additional note about this entry.
        """
        self.activity = activity
        self.date = date
        self.n = float (n)
        self.error = float (error)
        self.note = note

    def __repr__ (self):
        return 'CountingEntry(activity="{0}", date="{1}", n={2}, error={3}, ' \
                'note="{4}")'.format (
                        self.activity.name, self.date,
                        self.n, self.error, self.note)

    def cmp (self):
        return lambda a, b: cmp (a.date, b.date)

    def __cmp__ (a, b):
        cmp_date = cmp (a.date, b.date)
        if cmp_date:
            return cmp_date
        cmp_n = cmp (a.n, b.n)
        if cmp_n:
            return cmp_n
        cmp_error = cmp (a.error, b.error)
        return cmp_error

class TimingEntry (object):

    """An entry in the Log."""

    def __init__ (self, activity, start_time, end_time, note=''):
        """Construct a TimingEntry.
        
        :type   activity: :class:`Activity`
        :param  activity: The Activity this CountingEntry relates to.

        :type   time: datetime.datetime
        :param  time: The quantity associated with this CountingEntry.

        :type   note: str
        :param  note: An additional note about this entry.
        """
        self.activity = activity
        self.start_time = start_time
        self.end_time = end_time
        self.note = note

    def __repr__ (self):
        return 'TimingEntry(activity="{0}", start_time="{1}", ' \
                'end_time="{2}", note="{3}")'.format (
                        self.activity.name, self.start_time, self.end_time,
                        self.note)

    def cmp (self):
        return lambda a, b: cmp (a.start_time, b.start_time)

    def __cmp__ (a, b):
        cmp_start = cmp (a.start_time, b.start_time)
        if cmp_start:
            return cmp_start
        cmp_end = cmp (a.end_time, b.end_time)
        return cmp_end

    def overlap_in_hours (self, t1, t2=None):
        """Get the amount of hours an entry contains during a given date or
        time range."""
        if t2 is None:
            t1 = datetime.datetime (t1.year, t1.month, t1.day, 0, 0, 0, 0)
            t2 = t1 + datetime.timedelta (days=1, microseconds=-1)
        s1 = self.start_time
        s2 = t1
        e1 = self.end_time
        e2 = t2
        dt = min (e1, e2) - max (s1, s2)
        if dt < datetime.timedelta (seconds=0):
            return 0
        else:
            return timedelta_to_seconds (dt) / 3600.

class Log (object):

    """A Log of daily activity."""

    def __init__ (self, title='', user=''):
        """Construct a Log.

        :type   title: str
        :param  title: The title of this Log.

        :type   user: str
        :param  user: The name of the user of this Log.
        """
        self.title = title
        self.user = user
        self.counting_activities = set ()
        self.timing_activities = set ()
        self.entries = {}

    def __repr__ (self):
        return 'Log(title="{0}", user="{1}")'.format (
                self.title, self.user)

    def add_activity (self, activity):
        """Add a CountingActivity or TimingActivity."""
        if activity.kind == 'counting':
            self.counting_activities.add (activity)
        elif activity.kind == 'timing':
            self.timing_activities.add (activity)
        else:
            raise TypeError ('" activity" must be a '
                    'CountingActivity or TimingActivity')
        if activity not in self.entries:
            self.entries[activity] = []

    def add_entry (self, entry):
        """Add entry to the log."""
        activity = entry.activity
        self.add_activity (activity)
        self.entries[activity].append (entry)
        self.entries[activity] = sorted (self.entries[activity],
                cmp=entry.cmp ())

    def create_entry (self, activity_name, *args, **kwargs):
        """Create a new :class:`Entry` and add it to the Log."""
        activity = self.get_activity (activity_name)
        if activity.kind == 'counting':
            entry = CountingEntry (activity, *args, **kwargs)
        else:
            entry = TimingEntry (activity, *args, **kwargs)
        self.add_entry (entry)
        return entry

    def change_units (self, activity_name, new_unit, factor):
        """Change units of activity with CountingActivity.change_units."""
        activity = self.get_activity (activity_name)
        activity.change_units (self.entries[activity], new_unit, factor)

    def get_activity (self, activity_name):
        """Get an :class:`Activity` instance."""
        for activity in self.counting_activities | self.timing_activities:
            if activity.name == activity_name:
                return activity
        else:
            raise ValueError ('no activity found with name "{0}"'.format (
                activity_name))

    def get_entries (self, activity_name):
        """Get the :class:`Entry` s for this activity_name."""
        return self.entries[self.get_activity (activity_name)]


def write_log_to_file (log, filename):
    sep = ' | '
    with open (filename, 'w') as f:
        def pr (*args, **kwargs):
            kwargs['file'] = f
            print (*args, **kwargs)

        pr (log.title)
        pr (log.user)
        pr ()

        counting_activities = log.counting_activities
        pr ('Counting Activities:')
        for activity in counting_activities:
            pr ('    {1}{0}{2}'.format (
                sep, activity.name, activity.unit))
        
        pr ()
        timing_activities = log.timing_activities
        pr ('Timing Activities:')
        for activity in timing_activities:
            pr ('    {0}'.format (activity.name))

        pr ()
        pr ('Counting Entries:')
        for activity in counting_activities:
            entries = log.entries[activity]
            for entry in entries:
                pr ('    {1}{0}{2}{0}{3}{0}{4}'.format (
                    sep, activity.name, entry.date, entry.n, entry.error))
                pr ('        {0}'.format (entry.note))
        pr ('(End)')

        pr ()
        pr ('Timing Entries:')
        for activity in timing_activities:
            entries = log.entries[activity]
            for entry in entries:
                pr ('    {1}{0}{2}{0}{3}'.format (
                    sep, activity.name, entry.start_time, entry.end_time))
                if entry.note:
                    pr ('        {0}'.format (entry.note))
        pr ('(End)')

def get_log_from_file (filename):
    sep = ' | '
    with open (filename, 'r') as f:
        orig_lines = f.readlines ()

    lines = []
    for orig_line in orig_lines:
        if re.match (r'\s*#', orig_line):
            continue
        i = orig_line.find ('#')
        if i >= 0:
            line = orig_line[:i]
        else:
            line = orig_line
        line = line.rstrip ()
        lines.append (line)
        
    all_lines = lines[:]
    title = lines.pop (0)
    user = lines.pop (0)

    lines.pop (0)
    counting_activity_lines = []
    lines.pop (0)
    while lines[0] != 'Timing Activities:':
        counting_activity_lines.append (lines.pop (0).strip ())
    counting_activity_lines.pop (-1)
    lines.pop (0)

    timing_activity_lines = []
    while lines[0] != 'Counting Entries:':
        timing_activity_lines.append (lines.pop (0).strip ())
    timing_activity_lines.pop (-1)
    lines.pop (0)

    timing_entry_start = lines.index ('Timing Entries:')
    counting_lines = lines[:timing_entry_start - 1]
    timing_lines = lines[timing_entry_start + 1:]

    log = Log (title=title, user=user)
    for activity_line in counting_activity_lines:
        name, unit = activity_line.strip ().split (sep)
        log.add_activity (CountingActivity (name, unit))

    for activity_line in timing_activity_lines:
        name = activity_line.strip ()
        log.add_activity (TimingActivity (name))

    num_counting_lines = len (counting_lines)
    i = 0

    def next_line_is_note (i, lines):
        out = False
        if i < len (lines) - 1:
            next_line = lines[i + 1]
            indent = len (re.match (r'( *)[^ ]?', next_line).group (1))
            if indent == 0 and next_line != '(End)':
                out = True
            if indent == 8:
                out = True
        return out

    while i < num_counting_lines:
        line = counting_lines[i].strip ()
        if line == '(End)':
            i += 1
            continue
        activity_name, date_str, n, error = line.split (sep)
        note = ''
        while next_line_is_note (i, counting_lines):
            i += 1
            new_note_line = counting_lines[i].strip ()
            note += new_note_line + '\n'
        note = note.strip ()
        date = datetime.date (*map (int, date_str.split ('-')))
        log.create_entry (activity_name, date, n, error=error, note=note)
        i += 1

    def datetime_from_str (s):
        match = re.match (
                r'(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})(.(\d+))?',
                s)
        Y, M, D, h, m, s = map (int, match.groups ()[:6])
        us_group = match.groups ()[-1]
        if us_group is not None:
            us = int (float ('0.' + us_group) * 1e6)
        else:
            us = 0
        return datetime.datetime (Y, M, D, h, m, s, us)

    num_timing_lines = len (timing_lines)
    i = 0
    while i < num_timing_lines:
        line = timing_lines[i].strip ()
        if line == '(End)':
            i += 1
            continue
        activity_name, start_time_str, end_time_str = line.split (sep)
        note = ''
        while next_line_is_note (i, timing_lines):
            i += 1
            new_note_line = timing_lines[i].strip ()
            note += new_note_line + '\n'
        note = note.strip ()
        start_time = datetime_from_str (start_time_str)
        end_time = datetime_from_str (end_time_str)
        entry = log.create_entry (activity_name, start_time, end_time, note=note)
        i += 1

    return log
