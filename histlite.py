# histlight.py

from __future__ import print_function, division

__doc__  = """Calculate and plot histograms easily.

Numerous solutions are possible and already exist for generating and plotting
histograms with matplotlib. This module aims to provide the minimal interface
needed to add this useful functionality to a matplotlib environment.

"""

import copy
import datetime
from itertools import izip
import numpy as np

def timedelta_to_seconds (dt):
    """Return the number of seconds a timedelta lasts as a float."""
    return dt.seconds + dt.microseconds / 1E6 + dt.days * 86400


class Binner (object):

    """Tool to generate :class:`Hist` instances."""

    def __init__ (self, bins=50, range=None):
        """Initialize a Binner.
        
        :type   bins: int or numpy.ndarray
        :param  bins: The bins to be passed to numpy.histogram().

        :type   range: tuple
        :param  range: The range to be passed to numpy.histogram().

        """
        self._bins = bins
        self._range = range

    @property
    def bins (self):
        """The bins to be passed to numpy.histogram()."""
        return self._bins

    @property
    def range (self):
        """The range to be passed to numpy.histogram()."""
        return self._range

    @property
    def kwargs (self):
        """The numpy.histogram() keyword arguments."""
        return dict (bins=self.bins, range=self.range)

    def hist (self, array, weights=None):
        """Create a :class:`Hist`."""
        if weights is None:
            weights = np.ones (len (array))
        idx = np.isfinite (array) * np.isfinite (weights)

        range = (self.range,) if self.range else None

        if idx.sum () == 0:
            ignored, bins = np.histogram ([1], weights=[0], bins=self.bins,
                    range=self.range)
            return Hist (
                    bins, np.zeros (len (bins) - 1), np.zeros (len (bins) - 1))

        result = np.histogramdd (array[idx], weights=weights[idx],
                bins=self.bins, range=range)
        values, bins = result[0], result[1][0]
        result = np.histogramdd (array[idx], weights=weights[idx]**2,
                bins=self.bins, range=range)
        errors = np.sqrt (result[0])

        return Hist (bins, values, errors)


class Line (object):

    """Base class for binned lines such as histograms."""

    def __init__ (self, bins, values, errors=None):
        """Initialize a Line.

        :type   bins: numpy.ndarray
        :param  bins: The bin edges.

        :type   values: numpy.ndarray
        :param  values: The bin values.

        :type   errors: numpy.ndarray
        :param  errors: The per-bin errors.
        """
        self.bins = np.asarray (bins)
        self.values = np.asarray (values)
        if errors is None:
            self.errors = np.zeros (len (values))
        else:
            self.errors = np.asarray (errors)

    def bins_match (a, b):
        """Check whether two Lines have matching bins.

        :type   a: :class:`Line`
        :param  a: The first object.
        
        :type   b: :class:`Line`
        :param  b: The second object.

        :return: Whether the bins match (bool).
        """
        return np.sum ((a.bins - b.bins)**2) == 0

    def __add__ (a, b):
        if a.__class__ is b.__class__:
            assert (a.bins_match (b))
            values = 1.0 * a.values + b.values
            errors = np.sqrt (a.errors**2 + b.errors**2)
            return a.__class__ (a.bins, values, errors)
        else:
            return a.__class__ (a.bins, values + b, errors)

    def __sub__ (a, b):
        if a.__class__ is b.__class__:
            assert (a.bins_match (b))
            values = 1.0 * a.values - b.values
            errors = np.sqrt (a.errors**2 - b.errors**2)
            return a.__class__ (a.bins, values, errors)
        else:
            return a.__class__ (a.bins, values + b, errors)

    def __mul__ (a, b):
        if isinstance (b, Line):
            assert (a.bins_match (b))
            values = a.values * b.values
            errors = values * np.sqrt (
                    (a.errors / a.values)**2 + (b.errors / b.values)**2)
            return Line (a.bins, values, errors)
        else:
            return a.__class__ (a.bins, b * a.values, abs (b) * a.errors)

    def __rmul__ (self, scalar):
        return self * scalar

    def __div__ (a, b):
        if isinstance (b, Line):
            assert (a.bins_match (b))
            values = a.values / b.values
            errors = values * np.sqrt (
                    (a.errors / a.values)**2 + (b.errors / b.values)**2)
            return Line (a.bins, values, errors)
        else:
            b = 1.0 * b
            return a.__class__ (a.bins, a.values / b, a.errors / b)

    __truediv__ = __div__

    @property
    def bins (self):
        """The bin boundaries."""
        return self._bins
    @bins.setter
    def bins (self, bins):
        self._bins = copy.deepcopy (bins)

    @property
    def values (self):
        """The bin values, or counts."""
        return self._values
    @values.setter
    def values (self, values):
        self._values = copy.deepcopy (values)

    @property
    def errors (self):
        """The bin value errors."""
        return self._errors
    @errors.setter
    def errors (self, errors):
        self._errors = copy.deepcopy (errors)

    @property
    def bin_centers (self):
        """The bin centers."""
        bins = self.bins
        first = bins[0]
        if isinstance (first, datetime.date):
            bins = np.array ([
                datetime.datetime (b.year, b.month, b.day, 0, 0, 0, 0)
                for b in bins ])
        first = bins[0]
        if isinstance (first, datetime.datetime):
            dts = np.array ([
                timedelta_to_seconds (b2 - b1)
                for (b1,b2) in izip (bins[:-1], bins[1:])])
            centers = np.array ([
                b + datetime.timedelta (seconds=.5 * dt)
                for (b,dt) in izip (bins[:-1], dts)])
        else:
            centers = bins[:-1] + (bins[1:] - bins[:-1]) / 2
        return centers


class Hist (Line):

    """A histogram."""

    def __init__ (self, bins, values, errors=None):
        """Initialize a Hist.

        All arguments are passed directly to the :class:`Line`
        constructor.

        """
        Line.__init__ (self, bins, values, errors)


    @property
    def sum (self):
        """The sum of the bin values."""
        return self.values.sum ()

    @property
    def integral (self):
        """The integral of the histogram."""
        return np.sum (self.values * (np.diff (self.bins)))

    @property
    def sum_normed (self):
        """A copy of this Hist normalized so the bin counts sum to 1."""
        return self / self.sum

    @property
    def integral_normed (self):
        """A copy of this Hist normalized so the integral is 1."""
        return self / self.integral

    @property
    def cumulative_right (self):
        """The cumulative histogram, adding to the right."""
        # TODO: include proper errors
        return Line (self.bins, self.values.cumsum ())

    @property
    def cumulative_left (self):
        """The cumulative histogram, adding to the left."""
        # TODO: include proper errors
        return Line (self.bins, self.sum - self.values.cumsum ())

    def efficiency (self, base_hist):
        """Get an efficiency plot for this Hist divided by base_hist.

        :type   base_hist: :class:`Hist`
        :param  base_hist: The base histogram, of which this one should be a
            subset.

        This method differs from __div__ in the way that errors are propagated.

        """
        keep = self
        orig = base_hist
        rej = orig - keep

        eff = keep / orig
        nkeep = keep.values
        nrej = rej.values
        eff.errors = np.sqrt (
                (nrej / (nkeep+nrej)**2 * keep.errors)**2
                + (-nkeep / (nkeep+nrej)**2 * rej.errors)**2 )
        return eff


class Style (object):

    """Simple style object for Lines."""

    def __init__ (self,
            line=True,
            markers=False,
            errorbars=False,
            errorcaps=False,
            **kwargs
            ):
        """Initialize a Style.

        :type   line: bool
        :param  line: Whether to draw a line.

        :type   markers: bool
        :param  markers: Whether to draw point markers.

        :type   errorbars: bool
        :param  errorbars: Whether to draw errorbars.

        :type   errorcaps: bool
        :param  errorcaps: Whether to draw error bar caps.

        All other keyword args are saved to be passed to
        matplotlib.axes.Axes.errorbar(). Note that linestyle should not be
        specified; if line == True, then linestyle='steps-mid' will be used.

        """
        self._kwargs = {}
        self.line = True
        self.markers = False
        self.errorbars = False
        self.errorcaps = False
        self.update (
                line=line, markers=markers,
                errorbars=errorbars, errorcaps=errorcaps,
                **kwargs)

    def update (self, **kwargs):
        """Update the keyword args with the given values."""
        self.line = kwargs.pop ('line', self.line)
        self.markers = kwargs.pop ('markers', self.markers)
        self.errorbars = kwargs.pop ('errorbars', self.errorbars)
        self.errorcaps = kwargs.pop ('errorcaps', self.errorcaps)
        self._kwargs.update (copy.deepcopy (kwargs))

    def copy (self, **kwargs):
        """Get a copy of this Style, updating the given keyword args.

        All arguments accepted by the :class:`Style` constructor may be given,
        including line, markers, errorbars, errorcaps, and arbitrary matplotlib
        arguments.
        
        """
        out = copy.deepcopy (self)
        out.update (**kwargs)
        return out

    @property
    def line (self):
        """Whether to draw a line."""
        return self._line
    @line.setter
    def line (self, line):
        self._line = line

    @property
    def markers (self):
        """Whether to draw point markers."""
        return self._markers
    @markers.setter
    def markers (self, markers):
        self._markers = markers
        if self.markers:
            if 'marker' not in self._kwargs:
                self._kwargs['marker'] = 'o'
        else:
            self._kwargs['marker'] = 'None'

    @property
    def errorbars (self):
        """Whether to draw error bars."""
        return self._errorbars
    @errorbars.setter
    def errorbars (self, errorbars):
        self._errorbars = errorbars
        if not self.errorbars:
            self._kwargs['elinewidth'] = np.finfo (float).tiny
        else:
            self._kwargs.pop ('elinewidth', None)

    @property
    def errorcaps (self):
        """Whether to draw error bar caps."""
        return self._errorcaps
    @errorcaps.setter
    def errorcaps (self, errorcaps):
        self._errorcaps = errorcaps
        if not self.errorcaps:
            self._kwargs['capsize'] = 0
        else:
            self._kwargs.pop ('capsize', None)

    @property
    def kwargs (self):
        """Keyword args for matplotlib.axes.Axes.errorbar()."""
        return copy.deepcopy (self._kwargs)


class Plotter (object):

    """Tool for plotting :class:`Line` objects."""

    def __init__ (self, axes,
            twin_axes=None,
            log=False,
            twin_log=None,
            expx=False):
        """Initialize a Plotter.

        :type   axes: matplotlib Axes
        :param  axes: The main axes on which to plot.

        :type   twin_axes: matplotlib Axes
        :param  twin_axes: The secondary-y axes, if already created with
            axes.twinx().

        :type   log: bool
        :param  log: Whether to use a log y scale on the main axes.

        :type   twin_log: bool
        :param  twin_log: Whether to use a log y scale on the twin x axes.
            (If not given, then same as log argument)

        :type   expx: bool
        :param  expx: If true, convert :math:`x` -> :math:`10^x`

        """
        self._axes = axes
        self._twin_axes = twin_axes
        self._log = log
        if twin_log is None:
            self._twin_log = self.log
        else:
            self._twin_log = twin_log
        self._lines = np.empty (0, dtype=Line)
        self._line_styles = np.empty (0, dtype=dict)
        self._line_axes = np.empty (0, dtype=str)
        self._expx = bool (expx)

    @property
    def axes (self):
        """The matplotlib Axes."""
        return self._axes

    @property
    def log (self):
        """Whether to use a log y scale on the main axes."""
        return self._log

    @property
    def twin_log (self):
        """Whether to use a log y scale on the twin axes."""
        return self._twin_log

    @property
    def expx (self):
        """If true, convert :math:`x` -> :math:`10^x`"""
        return self._expx

    @property
    def twin_axes (self):
        """The matplotlib twinx Axes."""
        return self._twin_axes

    @property
    def lines (self):
        """The list of :class:`Lines` for this Plotter."""
        return self._lines

    @property
    def line_styles (self):
        """The list of keyword argument dicts for this Plotter."""
        return self._line_styles

    @property
    def line_axes (self):
        """The list of axes specifications for this Plotter (elements are
        'main' or 'twin')."""
        return self._line_axes


    def add (self, line_to_add,
            twin=False,
            style=None,
            **kwargs
            ):
        """Add a Line to the Plotter.

        :type   line_to_add: :class:`Line`
        :param  line_to_add: The line.

        :type   twin: bool
        :param  twin: Whether to use the secondary axes (default: use main axes)

        :type   errors: bool
        :param  errors: Whether to show errors for this particular Line.

        :type   style: :class:`Style`
        :param  style: The style for this line.

        If additional keyword arguments are given, then this line is plotted
        with a Style containing these extra keyword arguments.

        """
        self._lines = np.append (self.lines, line_to_add)
        if twin:
            self._line_axes = np.append (self.line_axes, 'twin')
        else:
            self._line_axes = np.append (self.line_axes, 'main')
        if style:
            style = style.copy (**kwargs)
        else:
            style = Style (**kwargs)
        self._line_styles = np.append (self.line_styles, style)


    def finish (self, legend=None):
        """Draw the lines.

        :type   legend: bool or dict
        :param  legend: If True or non-empty dict, draw a legend. If dict, use
            as keyword arguments for matplotlib.axes.Axes.legend.

        After this call, self.mpl_lines will be the matplotlib Line2D objects
        and self.mpl_labels will be the corresponding labels.
        
        """
        self.mpl_lines = np.empty (0, dtype=object)
        self.labels = np.empty (0, dtype=str)
        for line, style, axes_name \
                in izip (self.lines, self.line_styles, self.line_axes):
            if axes_name == 'main':
                axes = self.axes
                log = self.log
            else:
                if self.twin_axes is None:
                    self._twin_axes = self.axes.twinx ()
                axes = self.twin_axes
                log = self.twin_log
            axes = self.axes if axes_name == 'main' else self.twin_axes
            prev_ymin, prev_ymax = axes.get_ylim ()
            x = line.bin_centers
            if self.expx:
                x = 10**x
            y = line.values
            yerr = line.errors
            kwargs = copy.deepcopy (style.kwargs)
            label = kwargs.get ('label', '')
            if style.line:
                kwargs['drawstyle'] = 'steps-mid'
            else:
                kwargs['linestyle'] = 'None'
            if not style.errorbars:
                yerr = np.zeros_like (line.errors)
                kwargs['capsize'] = 0
            mpl_line, mpl_errorcaps, mpl_errorbars = axes.errorbar (
                    x, y, yerr, **kwargs)
            if style.line:
                # get left of first bin, right of last bin
                bins = line.bins
                if self.expx:
                    bins = 10**bins
                x1 = list (reversed ([bins[0], x[0]]))
                x2 = [bins[-1], x[-1]]
                y1 = [y[0], y[0]]
                y2 = [y[-1], y[-1]]
                zorder = kwargs.pop ('zorder', 0)
                zorder -= .01
                color = mpl_line.get_color ()
                drawstyle= 'steps-post'
                line_kwargs = dict (
                        drawstyle=drawstyle, color=color, zorder=zorder)
                def keep (key):
                    if key in kwargs:
                        line_kwargs[key] = kwargs[key]
                keep ('lw'), keep ('linewidth'), keep ('alpha')
                keep ('ls'), keep ('linestyle')
                axes.plot (x1, y1, **line_kwargs)
                axes.plot (x2, y2, **line_kwargs)
            if log:
                axes.set_yscale ('log')
                if np.sum (y>0) > 0:
                    # don't let errorbars make the scale crazy
                    min_accepted_ymin = min (prev_ymin, .1 * np.min (y[y>0]))
                    new_ymin, new_ymax = axes.get_ylim ()
                    final_ymin = max (new_ymin, min_accepted_ymin)
                    axes.set_ylim (ymin=final_ymin)

            self.mpl_lines = np.append (self.mpl_lines, mpl_line)
            self.labels = np.append (self.labels, label)

        if self.expx:
            self.axes.set_xscale ('log')

        if legend:
            if legend is True:
                legend = {}
            axes = self.twin_axes or self.axes
            self.legend = axes.legend (self.mpl_lines, self.labels, **legend)

    def old__finish (self, legend=None):
        """Draw the lines.

        :type   legend: bool or dict
        :param  legend: If True or non-empty dict, draw a legend. If dict, use
            as keyword arguments for matplotlib.axes.Axes.legend.

        After this call, self.mpl_lines will be the matplotlib Line2D objects
        and self.mpl_labels will be the corresponding labels.
        
        """
        self.mpl_lines = np.empty (0, dtype=object)
        self.labels = np.empty (0, dtype=str)
        for line, style, axes_name \
                in izip (self.lines, self.line_styles, self.line_axes):
            if axes_name == 'main':
                axes = self.axes
                log = self.log
            else:
                if self.twin_axes is None:
                    self._twin_axes = self.axes.twinx ()
                axes = self.twin_axes
                log = self.twin_log
            axes = self.axes if axes_name == 'main' else self.twin_axes
            prev_ymin, prev_ymax = axes.get_ylim ()
            x = line.bin_centers
            y = line.values
            yerr = line.errors
            kwargs = copy.deepcopy (style.kwargs)
            label = kwargs.get ('label', '')
            if style.line:
                kwargs['linestyle'] = 'steps-mid'
            else:
                kwargs['linestyle'] = 'None'
            if not style.errorbars:
                yerr = np.zeros_like (line.errors)
                kwargs['capsize'] = 0
            mpl_line, mpl_errorcaps, mpl_errorbars = axes.errorbar (
                    x, y, yerr, **kwargs)
            if style.line:
                # get left of first bin, right of last bin
                x = line.bins
                y = np.append (line.values, line.values[-1])
                zorder = kwargs.pop ('zorder', 0)
                zorder -= .01
                color = mpl_line.get_color ()
                linestyle= 'steps-post'
                line_kwargs = dict (
                        linestyle=linestyle, color=color, zorder=zorder)
                def keep (key):
                    if key in kwargs:
                        line_kwargs[key] = kwargs[key]

                keep ('lw'), keep ('linewidth'), keep ('alpha')
                axes.plot (x, y, **line_kwargs)
            if log:
                axes.set_yscale ('log')
                if np.sum (y>0) > 0:
                    # don't let errorbars make the scale crazy
                    min_accepted_ymin = min (prev_ymin, .1 * np.min (y[y>0]))
                    new_ymin, new_ymax = axes.get_ylim ()
                    final_ymin = max (new_ymin, min_accepted_ymin)
                    axes.set_ylim (ymin=final_ymin)

            self.mpl_lines = np.append (self.mpl_lines, mpl_line)
            self.labels = np.append (self.labels, label)

        if legend:
            if legend is True:
                legend = {}
            axes = self.twin_axes or self.axes
            self.legend = axes.legend (self.mpl_lines, self.labels, **legend)
