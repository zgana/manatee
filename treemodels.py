# treemodels.py

import gtk

from debug import *


class CountingActivitiesModel (gtk.GenericTreeModel):

    """Gtk TreeModel for CountingActivity's in a Log."""

    def __init__ (self, log):
        gtk.GenericTreeModel.__init__ (self)
        self.log = log

    @property
    def n_rows (self):
        return len (self.log.counting_activities)

    # Implementation of gtk.GenericTreeModel

    def on_get_flags (self):
        return gtk.TREE_MODEL_LIST_ONLY

    def on_get_n_columns (self):
        return 2

    def on_get_column_type (self, index):
        return str

    def on_get_iter (self, path):
        if len (self.log.counting_activities):
            return path[0]

    def on_get_path (self, rowref):
        return (rowref,)

    def on_get_value (self, row, col):
        if len (self.log.counting_activities) == 0:
            return None
        activity = sorted (self.log.counting_activities)[row]
        if col == 0:
            return activity.name
        elif col == 1:
            return activity.unit
        else:
            return None
        
    def on_iter_next (self, rowref):
        if rowref == self.n_rows - 1 or self.n_rows == 0:
            return None
        else:
            return rowref + 1

    def on_iter_children (self, parent):
        return 0                # TODO: is this right?

    def on_iter_has_child (self, rowref):
        return False

    def on_iter_n_children (self, rowref):
        if rowref:
            return 0
        else:
            return self.n_rows

    def on_iter_nth_child (self, parent, n):
        if parent:
            return None
        elif n < self.n_rows:
            return n
        else:
            return None

    def on_iter_parent (self, child):
        return None

class TimingActivitiesModel (gtk.GenericTreeModel):

    """Gtk TreeModel for TimingActivity's in a Log."""

    def __init__ (self, log):
        gtk.GenericTreeModel.__init__ (self)
        self.log = log

    @property
    def n_rows (self):
        return len (self.log.timing_activities)

    # Implementation of gtk.GenericTreeModel

    def on_get_flags (self):
        return gtk.TREE_MODEL_LIST_ONLY

    def on_get_n_columns (self):
        return 1

    def on_get_column_type (self, index):
        return str

    def on_get_iter (self, path):
        if len (self.log.timing_activities):
            return path[0]

    def on_get_path (self, rowref):
        return (rowref,)

    def on_get_value (self, row, col):
        if len (self.log.timing_activities) == 0:
            return None
        activity = sorted (self.log.timing_activities)[row]
        if col == 0:
            return activity.name
        else:
            return None
        
    def on_iter_next (self, rowref):
        if rowref == self.n_rows - 1 or self.n_rows == 0:
            return None
        else:
            return rowref + 1

    def on_iter_children (self, parent):
        return 0                # TODO: is this right?

    def on_iter_has_child (self, rowref):
        return False

    def on_iter_n_children (self, rowref):
        if rowref:
            return 0
        else:
            return self.n_rows

    def on_iter_nth_child (self, parent, n):
        if parent:
            return None
        elif n < self.n_rows:
            return n
        else:
            return None

    def on_iter_parent (self, child):
        return None

class CountingEntriesModel (gtk.GenericTreeModel):

    """Gtk TreeModel for CountingEntry's in a Log."""

    def __init__ (self, log, activity_name):
        gtk.GenericTreeModel.__init__ (self)
        self.log = log
        self.activity_name = activity_name

    @property
    def entries (self):
        return self.log.get_entries (self.activity_name)

    @property
    def n_rows (self):
        return len (self.entries)

    # Implementation of gtk.GenericTreeModel

    def on_get_flags (self):
        return gtk.TREE_MODEL_LIST_ONLY

    def on_get_n_columns (self):
        return 3

    def on_get_column_type (self, index):
        return str

    def on_get_iter (self, path):
        if len (self.entries):
            return path[0]

    def on_get_path (self, rowref):
        return (rowref,)

    def on_get_value (self, row, col):
        if self.n_rows == 0:
            return None
        entry = self.entries[row]
        if col == 0:
            return str (entry.date)
        elif col == 1:
            return str (entry.n)
        elif col == 2:
            return str (entry.error)
        elif col == 3:
            return str (entry.note)
        else:
            return None
        
    def on_iter_next (self, rowref):
        if rowref == self.n_rows - 1 or self.n_rows == 0:
            return None
        else:
            return rowref + 1

    def on_iter_children (self, parent):
        return 0                # TODO: is this right?

    def on_iter_has_child (self, rowref):
        return False

    def on_iter_n_children (self, rowref):
        if rowref:
            return 0
        else:
            return self.n_rows

    def on_iter_nth_child (self, parent, n):
        if parent:
            return None
        elif n < self.n_rows:
            return n
        else:
            return None

    def on_iter_parent (self, child):
        return None

class TimingEntriesModel (gtk.GenericTreeModel):

    """Gtk TreeModel for TimingEntry's in a Log."""

    def __init__ (self, log, activity_name):
        gtk.GenericTreeModel.__init__ (self)
        self.log = log
        self.activity_name = activity_name

    @property
    def entries (self):
        return self.log.get_entries (self.activity_name)

    @property
    def n_rows (self):
        return len (self.entries)

    # Implementation of gtk.GenericTreeModel

    def on_get_flags (self):
        return gtk.TREE_MODEL_LIST_ONLY

    def on_get_n_columns (self):
        return 2

    def on_get_column_type (self, index):
        return str

    def on_get_iter (self, path):
        if len (self.entries):
            return path[0]

    def on_get_path (self, rowref):
        return (rowref,)

    def on_get_value (self, row, col):
        def fmt (t):
            return '{0:04d}-{1:02d}-{2:02d} {3:02d}:{4:02d}'.format (
                    t.year, t.month, t.day, t.hour, t.minute)
        if self.n_rows == 0:
            return None
        entry = self.entries[row]
        if col == 0:
            return fmt (entry.start_time)
        elif col == 1:
            return fmt (entry.end_time)
        elif col == 2:
            return str (entry.note)
        else:
            return None
        
    def on_iter_next (self, rowref):
        if rowref == self.n_rows - 1 or self.n_rows == 0:
            return None
        else:
            return rowref + 1

    def on_iter_children (self, parent):
        return 0                # TODO: is this right?

    def on_iter_has_child (self, rowref):
        return False

    def on_iter_n_children (self, rowref):
        if rowref:
            return 0
        else:
            return self.n_rows

    def on_iter_nth_child (self, parent, n):
        if parent:
            return None
        elif n < self.n_rows:
            return n
        else:
            return None

    def on_iter_parent (self, child):
        return None

class ActivityDrawModel (gtk.GenericTreeModel):

    """Gtk TreeModel for drawing Activity's in a Log."""

    def __init__ (self, activities):
        gtk.GenericTreeModel.__init__ (self)
        self.activities = sorted (activities)
        self.checks = [
                False for activity in self.activities]
        n = len (self.activities)
        mpl_colors = [
                (0.0, 0.0, 1.0),
                (0.0, 0.5, 0.0),
                (1.0, 0.0, 0.0),
                (0.0, 0.75, 0.75),
                (0.75, 0, 0.75),
                (0.75, 0.75, 0),
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 1.0) ]
        n_color = len (mpl_colors)
        self.colors = [
                gtk.gdk.Color (*mpl_colors[i % n_color]) for i in xrange (n)]
        self.alphas = [
                int (.8 * 65535) for activity in self.activities]

    @property
    def n_rows (self):
        return len (self.activities)

    # toggle
    def toggle (self, path):
        row = int (path)
        self.checks[row] = not self.checks[row]

    # Implementation of gtk.GenericTreeModel

    def on_get_flags (self):
        return gtk.TREE_MODEL_LIST_ONLY

    def on_get_n_columns (self):
        return 3

    def on_get_column_type (self, index):
        if index == 0:
            return bool
        elif index == 1:
            return str
        elif index == 2:
            return gtk.gdk.Pixbuf

    def on_get_iter (self, path):
        if self.n_rows:
            return path[0]

    def on_get_path (self, rowref):
        return (rowref,)

    def on_get_value (self, row, col):
        if self.n_rows == 0:
            return None
        activity = sorted (self.activities)[row]
        if col == 0:
            return self.checks[row]
        elif col == 1:
            return activity.name
        else:
            pb = gtk.gdk.Pixbuf (
                    gtk.gdk.COLORSPACE_RGB, True, 8, 16, 16)
            color = self.colors[row]
            color_str = '{0:02x}{1:02x}{2:02x}{3:02x}'.format (
                    color.red / 256, color.green / 256, color.blue / 256,
                    self.alphas[row] / 256)
            pb.fill (int (color_str, 16))
            return pb
        
    def on_iter_next (self, rowref):
        if rowref == self.n_rows - 1 or self.n_rows == 0:
            return None
        else:
            return rowref + 1

    def on_iter_children (self, parent):
        return 0                # TODO: is this right?

    def on_iter_has_child (self, rowref):
        return False

    def on_iter_n_children (self, rowref):
        if rowref:
            return 0
        else:
            return self.n_rows

    def on_iter_nth_child (self, parent, n):
        if parent:
            return None
        elif n < self.n_rows:
            return n
        else:
            return None

    def on_iter_parent (self, child):
        return None
