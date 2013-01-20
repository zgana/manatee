# mainwindow.py

from __future__ import division, print_function

import datetime
from itertools import izip
import os
import sys

import pygtk
pygtk.require ('2.0')
import gtk
if gtk.pygtk_version < (2, 4, 0):
    print ('PyGtk 2.4.0 or later is required.')
    raise SystemExit
import gobject
import pango

import matplotlib as mpl
import matplotlib.backends.backend_gtkagg as mplgtkagg
import numpy as np

import manateelog
from manateelog import Log, CountingActivity, TimingActivity
from treemodels import *
from vars_class import Vars
from debug import LOGGER, LOG_F


def printerr (*a, **kw):
    if 'file' not in kw:
        kw['file'] = sys.stderr
    print (*a, **kw)

def remove_first_child (widget):
    children = widget.get_children ()
    if children:
        widget.remove (children[0])

def remove_last_child (widget):
    children = widget.get_children ()
    if children:
        widget.remove (children[-1])

def make_label (label):
    label = gtk.Label (label)
    xalign, yalign = label.get_alignment ()
    xalign = 0
    label.set_alignment (xalign, yalign)
    return label

def cell_renderer_wrapped_note ():
    cell = gtk.CellRendererText ()
    cell.set_property ('wrap-width', 600)
    cell.set_property ('wrap-mode', pango.WRAP_WORD)
    return cell

class MainWindow (object):

    def __init__ (self, app, log=None):
        self.app = app
        self.window = None
        self.pad = 10
        self.status_keys = []
        self.was_modified = False
        if log:
            self.set_log (log)
        else:
            self.set_log (Log ())

    def main (self):
        LOG_F ()
        gtk.main ()

    def set_log (self, log):
        LOG_F ()
        if self.window is None:
            self.window = gtk.Window (gtk.WINDOW_TOPLEVEL)
            self.window.connect ('delete_event', self.cb_delete_event)
        else:
            remove_first_child (self.window)
        self.menu = Vars ()
        self.events = Vars ()
        self.log = log
        self.build_log_window ()
        self.set_title ()
        if self.app.filename:
            self.set_status ('load', 'Loaded {0}.'.format (self.app.filename))


    # building the GUI -------------------------------------------------------

    def build_log_window (self):
        """Assemble the underlying gtk.Window."""
        LOG_F ()
        self.build_menu ()
        self.build_notebook ()
        self.window.show_all ()

    def build_menu (self):
        LOG_F ()
        self.vbox_menu = gtk.VBox (False, 2)
        self.window.add (self.vbox_menu)
        self.uim = gtk.UIManager ()
        self.accel_group = self.uim.get_accel_group ()
        self.window.add_accel_group (self.accel_group)
        self.menu.ag = gtk.ActionGroup ('base action group')
        self.menu.ag.add_actions (
            [
            ('File', None, '_File', None, None, None),
            ('New', gtk.STOCK_NEW, None, '<control>n', None, self.cb_new),
            ('Open', gtk.STOCK_OPEN, None, '<control>o', None, self.cb_open),
            ('Save', gtk.STOCK_SAVE, None, '<control>s', None, self.cb_save),
            ('Save As', gtk.STOCK_SAVE_AS, None, '<control><shift>s', None,
                self.cb_save_as),
            ('Quit', gtk.STOCK_QUIT, None, '<control>q', None, self.cb_quit),
            ]
        )
        self.menu.ui = """
        <ui>
            <menubar name='MenuBar'>
                <menu action='File'>
                    <menuitem action='New' />
                    <menuitem action='Open' />
                    <separator />
                    <menuitem action='Save' />
                    <menuitem action='Save As' />
                    <separator />
                    <menuitem action='Quit' />
                </menu>
            </menubar>
        </ui>
        """
        self.uim.insert_action_group (self.menu.ag, 0)
        self.uim.add_ui_from_string (self.menu.ui)
        self.menu.bar = self.uim.get_widget ('/MenuBar')
        self.vbox_menu.pack_start (self.menu.bar, False, False, 0)

    def build_notebook (self):
        """Set up main notebook."""
        LOG_F ()
        self.notebook = gtk.Notebook ()
        self.notebook.set_size_request (900, 600)

        self.setup = Vars ()
        self.counting = Vars ()
        self.timing = Vars ()
        self.ana = Vars ()

        self.setup.box_main = gtk.VBox (False, 5)
        self.counting.box_main = gtk.VBox (False, 5)
        self.timing.box_main = gtk.VBox (False, 5)
        self.ana.box_main = gtk.VBox (False, 5)

        self.notebook.append_page (
                self.setup.box_main, gtk.Label ('Setup'))
        self.notebook.append_page (
                self.counting.box_main, gtk.Label ('Counting Entries'))
        self.notebook.append_page (
                self.timing.box_main, gtk.Label ('Timing Entries'))
        self.notebook.append_page (
                self.ana.box_main, gtk.Label ('Analysis'))

        self.build_pane_setup ()
        self.build_pane_counting_entries ()
        self.build_pane_timing_entries ()
        self.build_pane_analysis ()
        self.notebook.set_current_page (1)
        self.vbox_menu.pack_start (self.notebook, True, True, 0)
        self.statusbar = gtk.Statusbar ()
        self.vbox_menu.pack_start (self.statusbar, False)

        self.notebook_ag = gtk.ActionGroup ('notebook action group')
        self.notebook_ag.add_actions ([
            ('setup', None, 'setup', '<alt>1', None,
                self.cb_notebook_page_switch)], 0)
        self.notebook_ag.add_actions ([
            ('counting', None, 'counting', '<alt>2', None,
                self.cb_notebook_page_switch)], 1)
        self.notebook_ag.add_actions ([
            ('timing', None, 'timing', '<alt>3', None,
                self.cb_notebook_page_switch)], 2)
        self.notebook_ag.add_actions ([
            ('analysis', None, 'analysis', '<alt>4', None,
                self.cb_notebook_page_switch)], 3)
        self.notebook_ui = """
        <ui>
            <accelerator action="setup" />
            <accelerator action="counting" />
            <accelerator action="timing" />
            <accelerator action="analysis" />
        </ui>"""
        self.uim.insert_action_group (self.notebook_ag, -1)
        merge_id = self.uim.add_ui_from_string (self.notebook_ui)

    def build_pane_setup (self):
        """Build the Setup pane."""
        LOG_F ()

        pad = self.pad
        hbox_args = (True, pad)
        vpack_args = dict (expand=False, fill=True, padding=2)
        label_pack_args = dict (expand=False, fill=True, padding=pad)
        entry_pack_args = dict (expand=True, fill=True, padding=pad)

        box_main = self.setup.box_main
        remove_first_child (box_main)
        box_main.set_border_width (pad)
        ### Meta
        frame_meta = gtk.Frame ('Log Properties')
        box_main.pack_start (frame_meta, expand=False)
        box_meta = gtk.HBox (False, pad)
        frame_meta.add (box_meta)
        table_meta = gtk.Table (2, 2)
        box_meta.pack_start (table_meta)
        table_meta.set_border_width (pad)
        table_meta.set_row_spacings (pad // 2)
        table_meta.set_col_spacings (pad // 2)
        ## Title
        table_meta.attach (make_label ('Title:'), 0, 1, 0, 1)
        self.setup.entry_title = gtk.Entry (max=0)
        table_meta.attach (self.setup.entry_title, 1, 2, 0, 1)
        self.setup.entry_title.set_text (self.log.title)
        ## User
        table_meta.attach (make_label ('User Name:'), 0, 1, 1, 2)
        self.setup.entry_user = gtk.Entry (max=0)
        table_meta.attach (self.setup.entry_user, 1, 2, 1, 2)
        self.setup.entry_user.set_text (self.log.user)
        ## buttons
        buttonbox = gtk.VButtonBox ()
        buttonbox.set_border_width (pad)
        box_meta.pack_start (buttonbox, expand=False, padding=pad)
        buttonbox.set_layout (gtk.BUTTONBOX_END)
        buttonbox.set_spacing (pad)
        button_update = gtk.Button (label='Update')
        buttonbox.pack_start (button_update)
        button_update.connect ('clicked', self.cb_setup_meta_update)


        ### CountingActivities
        frame_counting = gtk.Frame ('Counting Activities')
        box_main.pack_start (frame_counting, True)
        box_counting = gtk.HBox (False, pad)
        frame_counting.add (box_counting)
        box_counting.set_border_width (pad)

        ## viewing / editing
        box_counting_left = gtk.VBox (False, pad)
        box_counting.pack_start (box_counting_left, True)
        self.setup.cam = CountingActivitiesModel (self.log)
        self.setup.cam_tv = gtk.TreeView (self.setup.cam)
        self.setup.cam_sw = gtk.ScrolledWindow ()
        box_counting_left.pack_start (self.setup.cam_sw, True)
        self.setup.cam_sw.add_with_viewport (self.setup.cam_tv)
        self.sync_counting_activities ()

        ## adding
        box_counting_add = gtk.HBox (False)
        box_counting_left.pack_start (box_counting_add, False)
        box_counting_add.pack_start (
                make_label ('name:'), False)
        self.setup.entry_counting_add_name = gtk.Entry (max=0)
        box_counting_add.pack_start (
                self.setup.entry_counting_add_name, padding=pad)
        box_counting_add.pack_start (
                make_label ('unit:'), False)
        self.setup.entry_counting_add_unit = gtk.Entry (max=0)
        box_counting_add.pack_start (
                self.setup.entry_counting_add_unit, padding=pad)

        ## buttons
        buttonbox = gtk.VButtonBox ()
        box_counting.pack_start (buttonbox, False, padding=pad)
        buttonbox.set_layout (gtk.BUTTONBOX_END)
        buttonbox.set_spacing (pad)
        remove_button = gtk.Button (label='Remove selected')
        remove_button.connect ('clicked', self.cb_setup_counting_remove)
        buttonbox.pack_start (remove_button)
        edit_button = gtk.Button (label='Edit selected')
        edit_button.connect ('clicked', self.cb_setup_counting_edit)
        buttonbox.pack_start (edit_button)
        add_button = gtk.Button (stock=gtk.STOCK_ADD)
        buttonbox.pack_start (add_button)
        add_button.connect ('clicked', self.cb_setup_counting_add)
        buttonbox.set_focus_chain ([add_button, edit_button, remove_button])

        ### TimingActivities
        frame_timing = gtk.Frame ('Timing Activities')
        box_main.pack_start (frame_timing, True)
        box_timing = gtk.HBox (False, pad)
        frame_timing.add (box_timing)
        box_timing.set_border_width (pad)

        ## viewing / editing
        box_timing_left = gtk.VBox (False, pad)
        box_timing.pack_start (box_timing_left, True)
        self.setup.tam = TimingActivitiesModel (self.log)
        self.setup.tam_tv = gtk.TreeView (self.setup.tam)
        self.setup.tam_sw = gtk.ScrolledWindow ()
        box_timing_left.pack_start (self.setup.tam_sw, True)
        self.setup.tam_sw.add_with_viewport (self.setup.tam_tv)
        self.sync_timing_activities ()

        ## adding
        box_timing_add = gtk.HBox (False)
        box_timing_left.pack_start (box_timing_add, False)
        box_timing_add.pack_start (
                make_label ('name:'), False)
        self.setup.entry_timing_add_name = gtk.Entry (max=0)
        box_timing_add.pack_start (
                self.setup.entry_timing_add_name, padding=pad)

        ## buttons
        buttonbox = gtk.VButtonBox ()
        box_timing.pack_start (buttonbox, False, padding=pad)
        buttonbox.set_layout (gtk.BUTTONBOX_END)
        buttonbox.set_spacing (pad)
        remove_button = gtk.Button (label='Remove selected')
        remove_button.connect ('clicked', self.cb_setup_timing_remove)
        buttonbox.pack_start (remove_button)
        edit_button = gtk.Button (label='Edit selected')
        edit_button.connect ('clicked', self.cb_setup_timing_edit)
        buttonbox.pack_start (edit_button)
        add_button = gtk.Button (stock=gtk.STOCK_ADD)
        buttonbox.pack_start (add_button)
        add_button.connect ('clicked', self.cb_setup_timing_add)
        buttonbox.set_focus_chain ([add_button, edit_button, remove_button])

    def build_pane_counting_entries (self):
        """Build the Counting Entries pane."""
        LOG_F ()
        pad = self.pad

        box_main = self.counting.box_main
        box_main.foreach (box_main.remove)
        box_main.set_border_width (pad)

        ## which activity?
        box_combo = gtk.HBox (False, pad)
        box_main.pack_start (box_combo, expand=False)
        box_combo.pack_start (
                make_label ('Activity:'), expand=False, padding=pad)
        combo = self.counting.combo = gtk.combo_box_new_text ()
        box_combo.pack_start (combo, expand=True, padding=pad)
        for activity in sorted (self.log.counting_activities):
            combo.append_text ('{0} [{1}]'.format (
                activity.name, activity.unit))
        combo.set_active (0)
        combo.connect ('changed', self.cb_counting_choose)

        ## entries label
        box_label = gtk.HBox (False, pad)
        box_main.pack_start (box_label, expand=False, padding=pad // 2)
        box_label.pack_start (
                make_label ('Existing entries:'), expand=False, padding=pad)

        ## the viewer
        self.counting.cem_sw = gtk.ScrolledWindow ()
        box_main.pack_start (self.counting.cem_sw, expand=True)
        self.sync_counting_entries ()

        ## add
        table_add = gtk.Table (2, 3)
        table_add.set_row_spacings (pad // 2)
        table_add.set_col_spacings (pad)
        box_main.pack_start (table_add, expand=False, padding=pad)
        table_add.attach (
                make_label ('date (Y/M/D):'), 0, 1, 0, 1)
        
        box_add = gtk.HBox (False, pad)
        table_add.attach (box_add, 1, 2, 0, 1)
        self.counting.spin_Y = gtk.SpinButton ()
        box_add.pack_start (self.counting.spin_Y, expand=False)
        box_add.pack_start (make_label ('/'), expand=False)
        self.counting.spin_M = gtk.SpinButton ()
        box_add.pack_start (self.counting.spin_M, expand=False)
        box_add.pack_start (make_label ('/'), expand=False)
        self.counting.spin_D = gtk.SpinButton ()
        self.setup_counting_entries_add ()
        self.counting.spin_Y.connect (
                'value-changed', self.cb_counting_add_change_month)
        self.counting.spin_M.connect (
                'value-changed', self.cb_counting_add_change_month)
        box_add.pack_start (self.counting.spin_D, expand=False)
        box_add.pack_start (gtk.VSeparator ())
        box_add.pack_start (make_label ('amount'), expand=False)
        self.counting.entry_n = gtk.Entry (max=0)
        box_add.pack_start (self.counting.entry_n, expand=True)
        w, h = self.counting.entry_n.get_size_request ()
        self.counting.entry_n.set_size_request (30, h)
        box_add.pack_start (make_label ('+/-'), expand=False)
        self.counting.entry_error = gtk.Entry (max=0)
        box_add.pack_start (self.counting.entry_error, expand=True)
        self.counting.entry_error.set_size_request (30, h)

        ## add - note
        table_add.attach (make_label ('Note:'), 0, 1, 1, 2)
        sw = gtk.ScrolledWindow ()
        table_add.attach (sw, 1, 2, 1, 2)
        self.counting.textview_note = gtk.TextView ()
        sw.add_with_viewport (self.counting.textview_note)
        sw.set_size_request (10, 50)
        self.counting.textview_note.set_accepts_tab (False)
        self.counting.textview_note.set_property ('wrap-mode', gtk.WRAP_WORD)

        ## buttons
        buttonbox = gtk.VButtonBox ()
        buttonbox.set_layout (gtk.BUTTONBOX_END)
        buttonbox.set_spacing (pad)
        table_add.attach (buttonbox, 2, 3, 1, 3)
        button_remove = gtk.Button (label='Remove selected')
        buttonbox.pack_start (button_remove)
        button_remove.connect ('clicked', self.cb_counting_rm_entry)
        button_edit = gtk.Button (label='Edit selected')
        buttonbox.pack_start (button_edit)
        button_edit.connect ('clicked', self.cb_counting_edit_entry)
        button_add = gtk.Button (stock=gtk.STOCK_ADD)
        buttonbox.pack_start (button_add)
        button_add.connect ('clicked', self.cb_counting_add_entry)
        buttonbox.set_focus_chain ([button_add, button_edit, button_remove])

    def build_pane_timing_entries (self):
        """Build the Timing Entries pane."""
        LOG_F ()
        pad = self.pad

        box_main = self.timing.box_main
        box_main.foreach (box_main.remove)
        box_main.set_border_width (pad)

        ## which activity?
        box_combo = gtk.HBox (False, pad)
        box_main.pack_start (box_combo, expand=False)
        box_combo.pack_start (
                make_label ('Activity:'), expand=False, padding=pad)
        combo = self.timing.combo = gtk.combo_box_new_text ()
        box_combo.pack_start (combo, expand=True, padding=pad)
        for activity in sorted (self.log.timing_activities):
            combo.append_text ('{0}'.format (activity.name))
        combo.set_active (0)
        combo.connect ('changed', self.cb_timing_choose)

        ## entries label
        box_label = gtk.HBox (False, 10)
        box_main.pack_start (box_label, expand=False, padding=pad // 2)
        box_label.pack_start (
                make_label ('Existing entries:'), expand=False, padding=pad)

        ## the viewer
        self.timing.tem_sw = gtk.ScrolledWindow ()
        box_main.pack_start (self.timing.tem_sw, expand=True)
        self.timing.tem_columns = {}
        self.sync_timing_entries ()

        ## add - start
        today = datetime.datetime.today ()

        table_add = gtk.Table (3, 3)
        table_add.set_row_spacings (pad // 2)
        table_add.set_col_spacings (pad)
        box_main.pack_start (table_add, expand=False, padding=pad)
        table_add.attach (
                make_label ('start date (Y/M/D):'), 0, 1, 0, 1)
        table_add.attach (
                make_label ('end date (Y/M/D):'), 0, 1, 1, 2)

        box_start_datetime = gtk.HBox (False, pad)
        table_add.attach (box_start_datetime, 1, 2, 0, 1)
        self.timing.spin_sY = gtk.SpinButton ()
        box_start_datetime.pack_start (self.timing.spin_sY, expand=False)
        box_start_datetime.pack_start (make_label ('/'), expand=False)
        self.timing.spin_sM = gtk.SpinButton ()
        box_start_datetime.pack_start (self.timing.spin_sM, expand=False)
        box_start_datetime.pack_start (make_label ('/'), expand=False)
        self.timing.spin_sD = gtk.SpinButton ()
        box_start_datetime.pack_start (self.timing.spin_sD, expand=False)
        box_start_datetime.pack_start (gtk.VSeparator (), expand=False)
        self.timing.spin_sh = gtk.SpinButton ()
        box_start_datetime.pack_start (make_label ('time (H:M):'), expand=False)
        box_start_datetime.pack_start (self.timing.spin_sh)
        box_start_datetime.pack_start (make_label (':'), expand=False)
        self.timing.spin_sm = gtk.SpinButton ()
        box_start_datetime.pack_start (self.timing.spin_sm)

        self.setup_timing_entries_add_start ()
        self.timing.spin_sY.connect (
                'value-changed', self.cb_timing_add_change_start_month)
        self.timing.spin_sM.connect (
                'value-changed', self.cb_timing_add_change_start_month)

        button_start_now = gtk.Button (label='Start now')
        table_add.attach (button_start_now, 2, 3, 0, 1)
        button_start_now.connect ('clicked', self.cb_timing_now, 'start')

        button_end_now = gtk.Button (label='End now')
        table_add.attach (button_end_now, 2, 3, 1, 2)
        button_end_now.connect ('clicked', self.cb_timing_now, 'end')

        ## add - end
        box_end_datetime = gtk.HBox (False, pad)
        table_add.attach (box_end_datetime, 1, 2, 1, 2)
        self.timing.spin_eY = gtk.SpinButton ()
        box_end_datetime.pack_start (self.timing.spin_eY, expand=False)
        box_end_datetime.pack_start (make_label ('/'), expand=False)
        self.timing.spin_eM = gtk.SpinButton ()
        box_end_datetime.pack_start (self.timing.spin_eM, expand=False)
        box_end_datetime.pack_start (make_label ('/'), expand=False)
        self.timing.spin_eD = gtk.SpinButton ()
        box_end_datetime.pack_start (self.timing.spin_eD, expand=False)

        box_end_datetime.pack_start (gtk.VSeparator (), expand=False)
        self.timing.spin_eh = gtk.SpinButton ()
        box_end_datetime.pack_start (make_label ('time (H:M):'), expand=False)
        box_end_datetime.pack_start (self.timing.spin_eh)
        box_end_datetime.pack_start (make_label (':'), expand=False)
        self.timing.spin_em = gtk.SpinButton ()
        box_end_datetime.pack_start (self.timing.spin_em)

        self.setup_timing_entries_add_end ()

        self.timing.spin_eY.connect (
                'value-changed', self.cb_timing_add_change_end_month)
        self.timing.spin_eM.connect (
                'value-changed', self.cb_timing_add_change_end_month)

        ## add - note
        table_add.attach (make_label ('Note:'), 0, 1, 2, 3)
        sw = gtk.ScrolledWindow ()
        table_add.attach (sw, 1, 2, 2, 3)
        self.timing.textview_note = gtk.TextView ()
        sw.add_with_viewport (self.timing.textview_note)
        sw.set_size_request (10, 50)
        self.timing.textview_note.set_accepts_tab (False)
        self.timing.textview_note.set_property ('wrap-mode', gtk.WRAP_WORD)

        ## buttons
        buttonbox = gtk.VButtonBox ()
        table_add.attach (buttonbox, 2, 3, 2, 3)
        buttonbox.set_layout (gtk.BUTTONBOX_END)
        buttonbox.set_spacing (pad)
        button_remove = gtk.Button (label='Remove selected')
        buttonbox.pack_start (button_remove)
        button_remove.connect ('clicked', self.cb_timing_rm_entry)
        button_edit = gtk.Button (label='Edit selected')
        buttonbox.pack_start (button_edit)
        button_edit.connect ('clicked', self.cb_timing_edit_entry)
        button_add = gtk.Button (stock=gtk.STOCK_ADD)
        buttonbox.pack_start (button_add)
        button_add.connect ('clicked', self.cb_timing_add_entry)
        buttonbox.set_focus_chain ([button_add, button_edit, button_remove])

    def build_pane_analysis (self):
        """Build the Analysis pane."""
        LOG_F ()
        pad = self.pad
        self.ana.plot_type = None

        box_main = self.ana.box_main
        box_main.foreach (box_main.remove)
        box_main.set_border_width (pad)

        box_combo = gtk.HBox (False, pad)
        box_main.pack_start (box_combo, False)
        box_combo.pack_start (
                make_label ('Plot type:'), False, padding=pad)
        combo = self.ana.combo = gtk.combo_box_new_text ()
        box_combo.pack_start (combo, True, padding=pad)
        combo.append_text ('line plot')
        combo.set_active (0)
        combo.connect ('changed', self.sync_ana_plot_update)

        paned = gtk.VPaned ()
        box_main.pack_start (paned)

        box_conf = gtk.HBox (True, pad)
        box_conf.set_border_width (pad)
        paned.add1 (box_conf)

        self.ana.cadm_sw = gtk.ScrolledWindow ()
        self.ana.cadm_sw.set_size_request (5, 150)
        box_conf.pack_start (self.ana.cadm_sw, True, padding=pad)
        self.ana.tadm_sw = gtk.ScrolledWindow ()
        box_conf.pack_start (self.ana.tadm_sw, True, padding=pad)
        self.sync_ana_activities ()

        box_opts = self.ana.box_opts = gtk.VBox (False, 0)
        box_conf.pack_start (box_opts)

        self.ana.frame_plot = gtk.Frame ('Plot')
        paned.add2 (self.ana.frame_plot)
        self.sync_ana_plot_update ()

    def build_plot_options_line (self):
        """Build the Analysis pane plot options frame."""
        LOG_F ()
        pad = self.pad
        self.ana.opts = Vars ()
        self.ana.plot_type = 0
        box_opts = self.ana.box_opts
        box_opts.foreach (box_opts.remove)

        box_bin = gtk.HBox (False, 0)
        box_opts.pack_start (box_bin, False)

        self.ana.opts.spin_bin = spin = gtk.SpinButton ()
        box_bin.pack_start (spin, False, padding=pad)
        spin.set_adjustment (gtk.Adjustment (
            value=1, lower=1, upper=sys.maxint, step_incr=1))
        spin.connect (
                'value-changed', self.sync_ana_plot_update)
        box_bin.pack_start (make_label ('days per bin'))


        self.ana.opts.check_zero = gtk.CheckButton ('Extend y-axis to 0',)
        box_opts.pack_start (self.ana.opts.check_zero, False, padding=pad)

        self.window.show_all ()


    def sync_counting_activities (self):
        """Sync counting activities view."""
        LOG_F ()

        remove_first_child (self.setup.cam_sw)
        self.setup.cam = CountingActivitiesModel (self.log)
        self.setup.cam_tv = gtk.TreeView (self.setup.cam)
        self.setup.cam_sw.add_with_viewport (self.setup.cam_tv)
        self.setup.cam_tv.connect (
                'row-activated', self.cb_setup_counting_select)

        cell = gtk.CellRendererText ()
        namecol = gtk.TreeViewColumn ('name', cell, text=0)
        namecol.set_resizable (True)
        self.setup.cam_tv.insert_column (namecol, 0)
        unitcol = gtk.TreeViewColumn ('unit', cell, text=1)
        unitcol.set_resizable (True)
        self.setup.cam_tv.insert_column (unitcol, 1)
        self.build_pane_counting_entries ()
        self.build_pane_analysis ()
        self.window.show_all ()

    def sync_timing_activities (self):
        """Sync timing activities view."""
        LOG_F ()

        remove_first_child (self.setup.tam_sw)
        self.setup.tam = TimingActivitiesModel (self.log)
        self.setup.tam_tv = gtk.TreeView (self.setup.tam)
        self.setup.tam_sw.add_with_viewport (self.setup.tam_tv)
        self.setup.tam_tv.connect (
                'row-activated', self.cb_setup_timing_select)

        cell = gtk.CellRendererText ()
        namecol = gtk.TreeViewColumn ('name', cell, text=0)
        namecol.set_resizable (True)
        self.setup.tam_tv.insert_column (namecol, 0)
        self.build_pane_timing_entries ()
        self.build_pane_analysis ()
        self.window.show_all ()

    def sync_counting_entries (self):
        """Sync counting entries view."""
        LOG_F ()

        if len (self.log.counting_activities) == 0:
            return

        activity_idx = self.counting.combo.get_active ()
        activity = sorted (self.log.counting_activities)[activity_idx]

        remove_first_child (self.counting.cem_sw)
        self.counting.cem = CountingEntriesModel (self.log, activity.name)
        self.counting.cem_tv = gtk.TreeView (self.counting.cem)
        self.counting.cem_sw.add_with_viewport (self.counting.cem_tv)
        self.counting.cem_tv.connect (
                'row-activated', self.cb_counting_select_entry)

        def add_col (name, idx):
            cell = gtk.CellRendererText ()
            if name == 'note':
                cell = cell_renderer_wrapped_note ()
            col = gtk.TreeViewColumn (name, cell, text=idx)
            col.set_resizable (True)
            self.counting.cem_tv.insert_column (col, idx)

        add_col ('date', 0)
        add_col ('n', 1)
        add_col ('+/-', 2)
        add_col ('note', 3)
        self.sync_ana_plot_update ()
        self.window.show_all ()

    def sync_timing_entries (self):
        """Sync timing entries view."""
        LOG_F ()

        if len (self.log.timing_activities) == 0:
            return

        activity_idx = self.timing.combo.get_active ()
        activity = sorted (self.log.timing_activities)[activity_idx]

        remove_first_child (self.timing.tem_sw)
        self.timing.tem = TimingEntriesModel (self.log, activity.name)
        self.timing.tem_tv = gtk.TreeView (self.timing.tem)
        self.timing.tem_sw.add_with_viewport (self.timing.tem_tv)
        self.timing.tem_tv.connect (
                'row-activated', self.cb_timing_select_entry)

        def add_col (name, idx):
            cell = gtk.CellRendererText ()
            if name == 'note':
                cell = cell_renderer_wrapped_note ()
            col = self.timing.tem_columns[name] = gtk.TreeViewColumn (
                    name, cell, text=idx)
            col.set_resizable (True)
            self.timing.tem_tv.insert_column (col, idx)

        add_col ('start time', 0)
        add_col ('end time', 1)
        add_col ('note', 2)
        self.sync_ana_plot_update ()
        self.window.show_all ()

    def sync_ana_activities (self):
        """Sync activities in Analysis pane."""
        LOG_F ()
        def do_sync (sw, activities):
            remove_first_child (sw)
            model = ActivityDrawModel (activities)
            model_tv = gtk.TreeView (model)
            sw.add_with_viewport (model_tv)

            cell_toggle = gtk.CellRendererToggle ()
            col_toggle = gtk.TreeViewColumn ('toggle', cell_toggle, active=0)
            model_tv.insert_column (col_toggle, 0)
            cell_toggle.connect (
                    'toggled', self.cb_ana_activity_toggle, model)

            cell_color = gtk.CellRendererPixbuf ()
            col_color = gtk.TreeViewColumn ('color', cell_color, pixbuf=2)
            col_color.set_fixed_width (20)
            model_tv.insert_column (col_color, 1)

            cell_name = gtk.CellRendererText ()
            col_name = gtk.TreeViewColumn ('name', cell_name, text=1)
            model_tv.insert_column (col_name, 2)
            col_name.set_resizable (True)

            model_tv.connect (
                'row-activated', self.cb_ana_activity_choose_color, model)
            return model

        self.ana.cadm = do_sync (self.ana.cadm_sw, self.log.counting_activities)
        self.ana.tadm = do_sync (self.ana.tadm_sw, self.log.timing_activities)

        self.window.show_all ()
    
    def sync_ana_plot_update (self, *args):
        """Update the analysis plot."""
        LOG_F ()
        try:
            self.ana.combo
        except:
            return
        self.ana_plot_clear ()
        if self.ana.combo.get_active () == 0:
            if self.ana.plot_type != 0:
                self.build_plot_options_line ()
                self.ana.plot_type = 0
            self.ana_plot_line ()
        self.window.show_all ()

    def set_title (self, title=None):
        LOG_F ()
        if title is None:
            log_title = self.log.title or 'Log'
            if self.log.user:
                title = '{0} - {1} - Manatee'.format (log_title, self.log.user)
            else:
                title = '{0} - Manatee'.format (log_title)
        self.title = title
        self.window.set_title (self.title)
        self.window.show_all ()

    def setup_counting_entries_add (self):
        LOG_F ()
        today = datetime.datetime.today ()
        adj_Y = gtk.Adjustment (
                value=today.year, lower=1900, upper=2200, step_incr=1)
        adj_M = gtk.Adjustment (
                value=today.month, lower=1, upper=12, step_incr=1)
        adj_D = gtk.Adjustment (
                value=today.day, lower=1, upper=31, step_incr=1)
        self.counting.spin_Y.set_adjustment (adj_Y)
        self.counting.spin_M.set_adjustment (adj_M)
        self.counting.spin_D.set_adjustment (adj_D)

    def setup_timing_entries_add_start (self):
        LOG_F ()
        today = datetime.datetime.today ()

        def setup (spin, value, lower, upper):
            adj = gtk.Adjustment (
                    value=value, lower=lower, upper=upper, step_incr=1)
            spin.set_adjustment (adj)
            spin.set_value (value)

        setup (self.timing.spin_sY, today.year, 1900, 2200)
        setup (self.timing.spin_sM, today.month, 1, 12)
        setup (self.timing.spin_sD, today.day, 1, 31)
        setup (self.timing.spin_sh, today.hour, 0, 23)
        setup (self.timing.spin_sm, today.minute, 0, 59)

    def setup_timing_entries_add_end (self):
        LOG_F ()
        today = datetime.datetime.today ()

        def setup (spin, value, lower, upper):
            adj = gtk.Adjustment (
                    value=value, lower=lower, upper=upper, step_incr=1)
            spin.set_adjustment (adj)
            spin.set_value (value)

        setup (self.timing.spin_eY, today.year, 1900, 2200)
        setup (self.timing.spin_eM, today.month, 1, 12)
        setup (self.timing.spin_eD, today.day, 1, 31)
        setup (self.timing.spin_eh, today.hour, 0, 23)
        setup (self.timing.spin_em, today.minute, 0, 59)


    # plotting ---------------------------------------------------------------

    def ana_plot_clear (self, *args):
        """Create the figure."""
        LOG_F ()
        self.ana.frame_plot.foreach (self.ana.frame_plot.remove)
        self.ana.frame_plot.set_label ('Plot')
        fig = self.ana.figure = mpl.figure.Figure (
                figsize=(6, 4), dpi=50)
        self.ana.canvas = mplgtkagg.FigureCanvasGTKAgg (self.ana.figure)
        self.ana.frame_plot.add (self.ana.canvas)

    def ana_plot_line (self):
        """Make a line plot."""
        LOG_F ()
        labels, xs, ys, errs, colors, alphas = [], [], [], [], [], []

        cadm = self.ana.cadm
        tadm = self.ana.tadm

        if np.sum (np.r_[cadm.checks, tadm.checks]) == 1:
            one_unit = True
        else:
            one_unit = False
        if np.sum (cadm.checks) == 0:
            one_unit = True


        bin_width = self.ana.opts.spin_bin.get_value_as_int ()

        for i, activity in enumerate (cadm.activities):
            if cadm.checks[i]:
                entries = self.log.entries[activity]
                if not len (entries):
                    continue
                ti = entries[0].date
                tf = entries[-1].date
                x = [datetime.date (ti.year, ti.month, ti.day)]
                xf = datetime.date (tf.year, tf.month, tf.day)
                while x[-1] < xf:
                    x.append (x[-1] + datetime.timedelta (days=bin_width))
                y = []
                err = []
                for this_x in x:
                    y.append (np.sum ([
                        entry.n for entry in entries
                        if entry.date == this_x]))
                    err.append (np.sqrt (np.sum ([
                        entry.error**2 for entry in entries
                        if entry.date == this_x])))
                x = np.array (x)
                y = np.array (y)
                err = np.array (err)
                scale = 1.1 * np.max (y + err)
                if one_unit:
                    labels.append ('{0} ({1})'.format (
                        activity.name, activity.unit))
                else:
                    labels.append ('{0} (1 / {1:.1f} {2})'.format (
                        activity.name, scale, activity.unit))
                xs.append (x)
                if one_unit:
                    unit = activity.unit
                    ys.append (y)
                    errs.append (err)
                else:
                    ys.append (y / scale)
                    errs.append (err / scale)
                color = cadm.colors[i]
                colormax = 65535
                colors.append ((
                    color.red / colormax,
                    color.green / colormax,
                    color.blue / colormax))
                alphas.append (cadm.alphas[i] / colormax)

        for i, activity in enumerate (tadm.activities):
            if tadm.checks[i]:
                entries = sorted (self.log.entries[activity])
                if not len (entries):
                    continue
                ti = entries[0].start_time
                tf = entries[-1].end_time
                x = [datetime.date (ti.year, ti.month, ti.day)]
                xf = datetime.date (tf.year, tf.month, tf.day)
                while x[-1] < xf:
                    x.append (x[-1] + datetime.timedelta (days=bin_width))
                y = []
                for this_x in x:
                    y.append (np.sum ([
                        entry.hours_in_date (this_x)
                        for entry in entries]))
                scale = 1.1 * np.max (y)
                if one_unit:
                    unit = 'hours'
                    labels.append ('{0} (hours)'.format (activity.name))
                else:
                    labels.append ('{0} (1 / {1:.1f} hours)'.format (
                        activity.name, scale))
                xs.append (x)
                if one_unit:
                    ys.append (y)
                else:
                    ys.append (y / scale)
                errs.append (None)
                color = tadm.colors[i]
                colormax = 65535
                colors.append ((
                    color.red / colormax,
                    color.green / colormax,
                    color.blue / colormax))
                alphas.append (cadm.alphas[i] / colormax)

        if not labels:
            return

        ax = self.ana.figure.add_subplot (111)
        ax.patch.set_facecolor ('white')
        for label, x, y, err, color, alpha in izip (
                labels, xs, ys, errs, colors, alphas):
            kwargs = dict (label=label, color=color, alpha=alpha,
                        linestyle='steps-mid', lw=1.4)
            if err is None:
                ax.plot (x, y, **kwargs)
            else:
                p, c, b = ax.errorbar (x, y - err, y + err, **kwargs)
                for thing in np.r_[c, b]:
                    thing.set_alpha (alpha)
        if self.ana.opts.check_zero:
            ax.set_ylim (ymin=0)
        ax.set_ylim (ymin=max (ax.get_ylim ()[0], 0))
        if not one_unit:
            ax.legend (loc='best')
        ax.set_xlabel ('date')
        if one_unit:
            ax.set_ylabel (unit)


    # callbacks --------------------------------------------------------------

    def cb_delete_event (self, widget, event, *args):
        """Handle the X11 delete event."""
        LOG_F ()
        self.cb_quit (widget)
        return False

    def cb_new (self, whence, *args):
        """Create a new Log."""
        LOG_F ()
        response = self.save_first ()
        if response == gtk.RESPONSE_CANCEL:
            return
        self.app.new_log ()
        self.set_status ('load', 'Created a new log.')
        
    def cb_open (self, whence, *args):
        """Handle the Open action."""
        LOG_F ()
        response = self.save_first ()
        if response == gtk.RESPONSE_CANCEL:
            return
        dialog = gtk.FileChooserDialog ('Open...',
                None, gtk.FILE_CHOOSER_ACTION_OPEN,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_OPEN, gtk.RESPONSE_OK)
                )
        dialog.set_default_response (gtk.RESPONSE_OK)

        def add_filt (description, pattern):
            filt = gtk.FileFilter ()
            filt.set_name (description)
            filt.add_pattern (pattern)
            dialog.add_filter (filt)

        add_filt ('Manatee files', '*.manatee')
        add_filt ('All files', '*')

        response = dialog.run ()
        if response == gtk.RESPONSE_OK:
            filename = dialog.get_filename ()
        else:
            filename = None
        if filename:
            self.app.load_file (filename)
        dialog.destroy ()

    def cb_save (self, whence, *args):
        """Handle the Save As action."""
        LOG_F ()
        self.app.save ()
        self.set_status ('load', 'Saved {0}.'.format (self.app.filename))

    def cb_save_as (self, whence, *args):
        """Handle the Save As action."""
        LOG_F ()

        dialog = gtk.FileChooserDialog ('Save As...',
                None, gtk.FILE_CHOOSER_ACTION_SAVE,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_SAVE, gtk.RESPONSE_OK)
                )
        dialog.set_default_response (gtk.RESPONSE_OK)

        def add_filt (description, pattern):
            filt = gtk.FileFilter ()
            filt.set_name (description)
            filt.add_pattern (pattern)
            dialog.add_filter (filt)

        add_filt ('Manatee files', '*.manatee')

        response = dialog.run ()
        if response == gtk.RESPONSE_OK:
            filename = dialog.get_filename ()
        else:
            filename = None
        if filename:
            self.app.save_as (filename)
            self.set_status ('load', 'Saved {0}.'.format (self.app.filename))
        dialog.destroy ()
        return response
        
    def cb_quit (self, whence, *args):
        """Quit."""
        LOG_F ()
        response = self.save_first ()
        if response != gtk.RESPONSE_CANCEL:
            gtk.main_quit ()

    def cb_notebook_page_switch (self, whence, page_num, *args):
        """Switch notebook page."""
        LOG_F ()
        self.notebook.set_current_page (page_num)

    def cb_setup_meta_update (self, whence, *args):
        """Update meta data."""
        LOG_F ()
        self.log.title = self.setup.entry_title.get_text ()
        self.log.user = self.setup.entry_user.get_text ()
        self.set_title ()
        self.modify ('meta', 'Updated log properties.')

    def cb_setup_counting_remove (self, whence, *args):
        """Remove a counting activity."""
        LOG_F ()
        selection = self.setup.cam_tv.get_selection ()
        cam, rows = selection.get_selected_rows ()
        if not rows:
            self.set_status ('counting', 'No activity selected.')
            return
        activity = sorted (self.log.counting_activities)[rows[0][0]]
        response = self.confirm (
                'Remove activity "{0}"?'.format (activity.name),
                'Confirm remove')
        if response == gtk.RESPONSE_OK:
            remove_first_child (self.setup.cam_sw)
            self.log.counting_activities.remove (activity)
            del self.log.entries[activity]
            self.sync_counting_activities ()
            self.modify (
                    'counting', 'Removed activity "{0}"'.format (activity.name))

    def cb_setup_counting_select (self, whence, *args):
        """Respond to selection of a counting activity."""
        LOG_F ()
        cam, rows = whence.get_selection ().get_selected_rows ()
        if not rows:
            return
        activity = sorted (self.log.counting_activities)[rows[0][0]]
        self.setup.entry_counting_add_name.set_text (activity.name)
        self.setup.entry_counting_add_unit.set_text (activity.unit)

    def cb_setup_counting_edit (self, whence, *args):
        """Edit a counting activity."""
        LOG_F ()
        cam, rows = self.setup.cam_tv.get_selection ().get_selected_rows ()
        if not rows:
            self.set_status ('counting', 'No activity selected.')
            return
        activity = sorted (self.log.counting_activities)[rows[0][0]]
        old_name, old_unit = activity.name, activity.unit
        new_name = self.setup.entry_counting_add_name.get_text ()
        new_unit = self.setup.entry_counting_add_unit.get_text ()
        if new_unit != old_unit:
            pad = self.pad
            dialog = gtk.Dialog ('Unit conversion',
                    self.window,
                    gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                        gtk.STOCK_OK, gtk.RESPONSE_OK))
            hbox = gtk.HBox (False, pad)
            dialog.vbox.pack_start (hbox)
            hbox.pack_start (make_label ('1 {0} = '.format (old_unit)),
                    False, padding=pad)
            entry = gtk.Entry (max=0)
            hbox.pack_start (entry, False, padding=pad)
            hbox.pack_start (make_label (new_unit))
            dialog.show_all ()
            response = dialog.run ()
            factor = float (entry.get_text ())
            dialog.destroy ()
            if response == gtk.RESPONSE_CANCEL:
                return
            self.log.change_units (activity.name, new_unit, factor)
        activity.name = new_name
        self.sync_counting_activities ()
        self.modify ('counting', 'Edited activity "{0}".'.format (
            activity.name))

    def cb_setup_counting_add (self, whence, *args):
        """Add a counting activity."""
        LOG_F ()
        name = self.setup.entry_counting_add_name.get_text ()
        unit = self.setup.entry_counting_add_unit.get_text ()
        remove_first_child (self.setup.cam_sw)
        self.log.add_activity (CountingActivity (name, unit=unit))
        self.sync_counting_activities ()
        self.modify ('counting', 'Added activity "{0}".'.format (name))

    def cb_setup_timing_remove (self, whence, *args):
        """Remove a timing activity."""
        LOG_F ()
        selection = self.setup.tam_tv.get_selection ()
        tam, rows = selection.get_selected_rows ()
        if not rows:
            self.set_status ('timing', 'No activity selected.')
            return
        activity = sorted (self.log.timing_activities)[rows[0][0]]
        response = self.confirm (
                'Remove activity "{0}"?'.format (activity.name),
                'Confirm remove')
        if response == gtk.RESPONSE_OK:
            remove_first_child (self.setup.tam_sw)
            self.log.timing_activities.remove (activity)
            del self.log.entries[activity]
            self.sync_timing_activities ()
            self.modify (
                'timing', 'Removed activity "{0}"'.format (activity.name))

    def cb_setup_timing_select (self, whence, *args):
        """Respond to selection of a timing activity."""
        LOG_F ()
        cam, rows = whence.get_selection ().get_selected_rows ()
        if not rows:
            return
        activity = sorted (self.log.timing_activities)[rows[0][0]]
        self.setup.entry_timing_add_name.set_text (activity.name)

    def cb_setup_timing_edit (self, whence, *args):
        """Edit a timing activity."""
        LOG_F ()
        cam, rows = self.setup.tam_tv.get_selection ().get_selected_rows ()
        if not rows:
            self.set_status ('timing', 'No activity selected.')
            return
        activity = sorted (self.log.timing_activities)[rows[0][0]]
        activity.name = self.setup.entry_timing_add_name.get_text ()
        self.sync_timing_activities ()
        self.modify ('timing', 'Edited activity "{0}"'.format (activity.name))

    def cb_setup_timing_add (self, whence, *args):
        """Add a timing activity."""
        LOG_F ()
        name = self.setup.entry_timing_add_name.get_text ()
        remove_first_child (self.setup.tam_sw)
        self.log.add_activity (TimingActivity (name))
        self.sync_timing_activities ()
        self.modify ('timing', 'Added activity "{0}"'.format (name))

    def cb_counting_choose (self, whence, *args):
        """Choose the counting activity."""
        LOG_F ()
        self.sync_counting_entries ()

    def cb_counting_select_entry (self, whence, *args):
        """Respond to selection of a counting entry."""
        LOG_F ()
        cam, rows = whence.get_selection ().get_selected_rows ()
        if not rows:
            return
        activity_idx = self.counting.combo.get_active ()
        activity = sorted (self.log.counting_activities)[activity_idx]
        entry = self.log.entries[activity][rows[0][0]]
        self.counting.spin_Y.set_value (entry.date.year)
        self.counting.spin_M.set_value (entry.date.month)
        self.counting.spin_D.set_value (entry.date.day)
        self.counting.entry_n.set_text (str (entry.n))
        self.counting.entry_error.set_text (str (entry.error))
        note_buffer = self.counting.textview_note.get_buffer ()
        note_buffer.set_text (entry.note)

    def cb_counting_rm_entry (self, whence, *args):
        """Remove a counting entry."""
        LOG_F ()
        selection = self.counting.cem_tv.get_selection ()
        cam, rows = selection.get_selected_rows ()
        if not len (rows):
            self.set_status ('counting', 'No entry selected.')
            return
        idx = rows[0][0]
        entries = self.counting.cem.entries
        entry = entries[idx]
        response = self.confirm ('Remove entry?', 'Confirm remove')
        if response == gtk.RESPONSE_OK:
            remove_first_child (self.counting.cem_sw)
            entries.pop (idx)
            self.sync_counting_entries ()
            self.modify (
                    'counting', 'Removed entry from {0}.'.format (entry.date))

    def cb_counting_edit_entry (self, whence, *args):
        """Edit a counting entry."""
        LOG_F ()
        cam, rows = self.counting.cem_tv.get_selection ().get_selected_rows ()
        if not rows:
            self.set_status ('counting', 'No entry selected.')
            return
        activity_idx = self.counting.combo.get_active ()
        activity = sorted (self.log.counting_activities)[activity_idx]
        entry = self.log.entries[activity][rows[0][0]]
        Y = self.counting.spin_Y.get_value_as_int ()
        M = self.counting.spin_M.get_value_as_int ()
        D = self.counting.spin_D.get_value_as_int ()
        n = float (self.counting.entry_n.get_text ())
        error = float (self.counting.entry_error.get_text ())
        note_buffer = self.counting.textview_note.get_buffer ()
        note = note_buffer.get_text (
                note_buffer.get_start_iter (),
                note_buffer.get_end_iter ())
        entry.date = datetime.date (Y, M, D)
        entry.n = n
        entry.error = error
        entry.note = note
        self.sync_counting_entries ()
        self.modify ('counting', 'Edited entry on {0}.'.format (entry.date))

    def cb_counting_add_entry (self, whence, *args):
        """Add a counting entry."""
        LOG_F ()
        Y = self.counting.spin_Y.get_value_as_int ()
        M = self.counting.spin_M.get_value_as_int ()
        D = self.counting.spin_D.get_value_as_int ()
        n = float (self.counting.entry_n.get_text ())
        error = float (self.counting.entry_error.get_text ())
        note_buffer = self.counting.textview_note.get_buffer ()
        note = note_buffer.get_text (
                note_buffer.get_start_iter (),
                note_buffer.get_end_iter ())
        entries = self.counting.cem.entries
        remove_first_child (self.counting.cem_sw)
        activity_idx = self.counting.combo.get_active ()
        activity = sorted (self.log.counting_activities)[activity_idx]
        date = datetime.date (Y, M, D)
        entry = self.log.create_entry (
                activity.name, date, n, error=error, note=note)
        self.sync_counting_entries ()
        self.counting.entry_n.set_text ('')
        self.counting.entry_error.set_text ('')
        self.modify ('counting', 'Added entry on {0}.'.format (entry.date))
        self.counting.spin_Y.grab_focus ()

    def cb_counting_add_change_month (self, whence, *args):
        """Limit the day according to the year and month."""
        LOG_F ()
        day = 26
        Y = self.counting.spin_Y.get_value_as_int ()
        M = self.counting.spin_M.get_value_as_int ()
        while True:
            day += 1
            try:
                datetime.date (Y, M, day)
            except:
                break
        self.counting.spin_D.set_range (1, day - 1)

    def cb_timing_choose (self, whence, *args):
        """Choose the timing activity."""
        LOG_F ()
        self.sync_timing_entries ()

    def cb_timing_select_entry (self, whence, *args):
        """Respond to selection of a counting entry."""
        LOG_F ()
        cam, rows = whence.get_selection ().get_selected_rows ()
        if not rows:
            return
        activity_idx = self.timing.combo.get_active ()
        activity = sorted (self.log.timing_activities)[activity_idx]
        entry = self.log.entries[activity][rows[0][0]]
        self.timing.spin_sY.set_value (entry.start_time.year)
        self.timing.spin_sM.set_value (entry.start_time.month)
        self.timing.spin_sD.set_value (entry.start_time.day)
        self.timing.spin_sh.set_value (entry.start_time.hour)
        self.timing.spin_sm.set_value (entry.start_time.minute)
        self.timing.spin_eY.set_value (entry.end_time.year)
        self.timing.spin_eM.set_value (entry.end_time.month)
        self.timing.spin_eD.set_value (entry.end_time.day)
        self.timing.spin_eh.set_value (entry.end_time.hour)
        self.timing.spin_em.set_value (entry.end_time.minute)
        note_buffer = self.timing.textview_note.get_buffer ()
        note_buffer.set_text (entry.note)

    def cb_timing_now (self, whence, when, *args):
        """Set the time to now."""
        LOG_F ()
        now = datetime.datetime.today ()
        if when == 'start':
            self.setup_timing_entries_add_start ()
        elif when == 'end':
            self.setup_timing_entries_add_end ()

    def cb_timing_rm_entry (self, whence, *args):
        """Remove a timing entry."""
        LOG_F ()
        selection = self.timing.tem_tv.get_selection ()
        cam, rows = selection.get_selected_rows ()
        if not len (rows):
            self.set_status ('timing', 'No entry selected.')
            return
        idx = rows[0][0]
        entries = self.timing.tem.entries
        entry = entries[idx]
        response = self.confirm ('Remove entry?', 'Confirm remove')
        if response == gtk.RESPONSE_OK:
            remove_first_child (self.timing.tem_sw)
            entries.pop (idx)
            self.sync_timing_entries ()
            self.modify ('timing', 'Removed entry starting at {0}'.format (
                entry.start_time))

    def cb_timing_edit_entry (self, whence, *args):
        """Edit a timing entry."""
        LOG_F ()
        cam, rows = self.timing.tem_tv.get_selection ().get_selected_rows ()
        if not rows:
            self.set_status ('timing', 'No entry selected.')
            return
        entries = self.timing.tem.entries
        entry = entries[rows[0][0]]
        sY = self.timing.spin_sY.get_value_as_int ()
        sM = self.timing.spin_sM.get_value_as_int ()
        sD = self.timing.spin_sD.get_value_as_int ()
        sh = self.timing.spin_sh.get_value_as_int ()
        sm = self.timing.spin_sm.get_value_as_int ()

        eY = self.timing.spin_eY.get_value_as_int ()
        eM = self.timing.spin_eM.get_value_as_int ()
        eD = self.timing.spin_eD.get_value_as_int ()
        eh = self.timing.spin_eh.get_value_as_int ()
        em = self.timing.spin_em.get_value_as_int ()

        note_buffer = self.timing.textview_note.get_buffer ()
        note = note_buffer.get_text (
                note_buffer.get_start_iter (),
                note_buffer.get_end_iter ())
        entry.start_time = datetime.datetime (sY, sM, sD, sh, sm)
        entry.end_time = datetime.datetime (eY, eM, eD, eh, em)
        entry.note = note
        self.sync_timing_entries ()
        self.modify ('timing', 'Edited entry starting at {0}'.format (
            entry.start_time))

    def cb_timing_add_entry (self, whence, *args):
        """Add a timing entry."""
        LOG_F ()
        sY = self.timing.spin_sY.get_value_as_int ()
        sM = self.timing.spin_sM.get_value_as_int ()
        sD = self.timing.spin_sD.get_value_as_int ()
        sh = self.timing.spin_sh.get_value_as_int ()
        sm = self.timing.spin_sm.get_value_as_int ()

        eY = self.timing.spin_eY.get_value_as_int ()
        eM = self.timing.spin_eM.get_value_as_int ()
        eD = self.timing.spin_eD.get_value_as_int ()
        eh = self.timing.spin_eh.get_value_as_int ()
        em = self.timing.spin_em.get_value_as_int ()

        note_buffer = self.timing.textview_note.get_buffer ()
        note = note_buffer.get_text (
                note_buffer.get_start_iter (),
                note_buffer.get_end_iter ())

        entries = self.timing.tem.entries
        remove_first_child (self.timing.tem_sw)
        activity_idx = self.timing.combo.get_active ()
        activity = sorted (self.log.timing_activities)[activity_idx]
        start_time = datetime.datetime (sY, sM, sD, sh, sm)
        end_time = datetime.datetime (eY, eM, eD, eh, em)
        entry = self.log.create_entry (
                activity.name, start_time, end_time, note=note)
        self.sync_timing_entries ()
        self.setup_timing_entries_add_start ()
        self.setup_timing_entries_add_end ()
        self.modify ('timing', 'Added entry starting at {0}'.format (
            entry.start_time))

    def cb_timing_add_change_start_month (self, whence, *args):
        """Limit the day according to the year and month."""
        LOG_F ()
        day = 26
        Y = self.timing.spin_sY.get_value_as_int ()
        M = self.timing.spin_sM.get_value_as_int ()
        while True:
            day += 1
            try:
                datetime.date (Y, M, day)
            except:
                break
        self.timing.spin_sD.set_range (1, day - 1)

    def cb_timing_add_change_end_month (self, whence, *args):
        """Limit the day according to the year and month."""
        LOG_F ()
        day = 26
        Y = self.timing.spin_eY.get_value_as_int ()
        M = self.timing.spin_eM.get_value_as_int ()
        while True:
            day += 1
            try:
                datetime.date (Y, M, day)
            except:
                break
        self.timing.spin_eD.set_range (1, day - 1)

    def cb_ana_activity_toggle (self, cell, path, model):
        """A counting activity was toggled for plotting."""
        LOG_F ()
        model.toggle (path)
        self.sync_ana_plot_update ()

    def cb_ana_activity_choose_color (self, whence, path, column, model):
        """Set the color of an activity."""
        LOG_F ()
        cam, rows = whence.get_selection ().get_selected_rows ()
        if not rows:
            return
        row = rows[0][0]
        activity = model.activities[row]
        dialog = gtk.ColorSelectionDialog ('Select color for "{0}"'.format (
            activity.name))
        dialog.colorsel.set_current_color (
                model.colors[row])
        dialog.colorsel.set_current_alpha (
                model.alphas[row])
        response = dialog.run ()
        dialog.destroy ()
        if response == gtk.RESPONSE_OK:
            new_color = dialog.colorsel.get_current_color ()
            new_alpha = dialog.colorsel.get_current_alpha ()
            model.colors[row] = new_color
            model.alphas[row] = new_alpha
        self.set_status (
                'ana', 'Updated color for "{0}"'.format (activity.name))
        self.sync_ana_plot_update ()

    # other ------------------------------------------------------------------

    def confirm (self, msg, title):
        LOG_F ()
        dialog = gtk.MessageDialog (
                self.window, gtk.DIALOG_MODAL,
                gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL,
                msg)
        dialog.set_title (title)
        response = dialog.run ()
        dialog.destroy ()
        return response

    def yes_no_cancel (self, msg, title):
        LOG_F ()
        dialog = gtk.MessageDialog (
                self.window, gtk.DIALOG_MODAL,
                gtk.MESSAGE_QUESTION, gtk.BUTTONS_NONE,
                msg)
        dialog.add_buttons (
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_NO, gtk.RESPONSE_NO,
                gtk.STOCK_YES, gtk.RESPONSE_YES)
        dialog.set_title (title)
        dialog.set_default_response (gtk.RESPONSE_YES)
        response = dialog.run ()
        dialog.destroy ()
        return response

    def save_first (self):
        LOG_F ()
        if not self.was_modified:
            return
        response = self.yes_no_cancel (
                'Save first?',
                'Last chance to save')
        if response == gtk.RESPONSE_YES:
            if self.app.filename:
                self.app.save ()
            else:
                response = self.cb_save_as (None)
        return response


    def set_status (self, key, msg):
        LOG_F ()
        if key not in self.status_keys:
            self.status_keys.append (key)
        context_id = self.status_keys.index (key)
        self.statusbar.push (context_id, msg)

    def modify (self, key, msg):
        LOG_F ()
        self.was_modified = True
        self.set_status (key, msg)
