from typing import TYPE_CHECKING

import wx

from . import monkey_patch


# Press and hold `x`, `y` or `z` and then click on one of the points in the plot
# and drag the point along the axis noted by the key that is being held down.
#
# Left click and drag rotates the plot.
# Right click and drag pans the plot.
# Mouse wheel zooms the plot.
#
# Code was added to remove the flicking that was seen when the plot is redrawn.

import wx
import matplotlib

matplotlib.rcParams[f'axes3d.xaxis.panecolor'] = (0.0, 0.0, 0.0, 0.0)
matplotlib.rcParams[f'axes3d.yaxis.panecolor'] = (0.0, 0.0, 0.0, 0.0)
matplotlib.rcParams[f'axes3d.yaxis.panecolor'] = (0.0, 0.0, 0.0, 0.0)
matplotlib.rcParams['grid.color'] = (0.5, 0.5, 0.5, 0.5)
matplotlib.rcParams['grid.linewidth'] = 0.5
matplotlib.rcParams['grid.linestyle'] = ':'
matplotlib.rcParams['axes.linewidth'] = 0.5
matplotlib.rcParams['axes.edgecolor'] = (0.45, 0.45, 0.45, 0.55)

matplotlib.rcParams['xtick.major.width'] = 0.5
matplotlib.rcParams['ytick.major.width'] = 0.5

matplotlib.rcParams['ytick.minor.width'] = 0.5
matplotlib.rcParams['ytick.minor.width'] = 0.5

matplotlib.use('WXAgg')

from ..wrappers.art3d import Path3DCollection  # NOQA

from mpl_toolkits.mplot3d import axes3d as _axes3d  # NOQA
import matplotlib.pyplot  # NOQA
import numpy as np  # NOQA

from wx.lib.agw import aui  # NOQA
from ..widgets import aui_toolbar  # NOQA
from .. import image as _image  # NOQA
from . import canvas as _canvas  # NOQA
from .inlays import axis_indicator  # NOQA
from .. import config as _config  # NOQA
from ..wrappers.wxkey_event import KeyEvent  # NOQA
from ..wrappers.wxmouse_event import MouseEvent  # NOQA
from .. import utils  # NOQA


if TYPE_CHECKING:
    from .. import ui


class Config(metaclass=_config.Config):
    axis_indicator = [0.88, 0.02, 0.10, 0.10]


class Editor3D(wx.Panel):

    ID_POINTER = wx.NewIdRef()
    ID_TRANSITION = wx.NewIdRef()
    ID_CONNECTOR = wx.NewIdRef()
    ID_TERMINAL = wx.NewIdRef()
    ID_SEAL = wx.NewIdRef()
    ID_WIRE = wx.NewIdRef()
    ID_SPLICE = wx.NewIdRef()
    ID_BUNDLE_COVER = wx.NewIdRef()
    ID_TPA_LOCK = wx.NewIdRef()
    ID_CPA_LOCK = wx.NewIdRef()

    def __init__(self, parent):
        self.mode = self.ID_POINTER

        self.mainframe: "ui.MainFrame" = parent.GetParent()
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.fig = matplotlib.pyplot.figure(figsize=(3.5, 3.5))

        ax = self.axes = _axes3d.Axes3D(self.fig, [-0.80, -0.95, 2.8, 2.8])

        self.fig.add_axes(ax)

        ax.set_xlim3d(-50, 50)
        ax.set_ylim3d(-50, 50)
        ax.set_zlim3d(-50, 50)

        inlay = self.inlay = axis_indicator.AxisIndicator(self.fig, Config.axis_indicator)
        self.canvas = _canvas.Canvas(self, wx.ID_ANY, self.fig, self.axes)

        ax.shareview(inlay)
        self.fig.add_axes(inlay)

        self.editor3d_toolbar = aui_toolbar.AuiToolBar(self.mainframe, style=aui.AUI_TB_GRIPPER | aui.AUI_TB_TEXT)
        self.editor3d_toolbar.SetToolBitmapSize((48, 48))

        pointer = _image.icons.pointer.resize(48, 48)
        transition = _image.icons.transition.resize(48, 48)
        connector = _image.icons.connector.resize(48, 48)
        terminal = _image.icons.terminal.resize(48, 48)
        seal = _image.icons.seal.resize(48, 48)
        wire = _image.icons.wire.resize(48, 48)
        splice = _image.icons.splice.resize(48, 48)
        bundle_cover = _image.icons.bundle_cover.resize(48, 48)
        tpa_lock = _image.icons.tpa_lock.resize(48, 48)
        cpa_lock = _image.icons.cpa_lock.resize(48, 48)

        btns = [
            (self.ID_POINTER, pointer, 'Pointer'),
            (self.ID_TRANSITION, transition, 'Transition'),
            (self.ID_CONNECTOR, connector, 'Connector'),
            (self.ID_TERMINAL, terminal, 'Terminal'),
            (self.ID_SEAL, seal, 'Seal'),
            (self.ID_WIRE, wire, 'Wire'),
            (self.ID_SPLICE, splice, 'Splice'),
            (self.ID_BUNDLE_COVER, bundle_cover, 'Bundle'),
            (self.ID_TPA_LOCK, tpa_lock, 'TPA'),
            (self.ID_CPA_LOCK, cpa_lock, 'CPA')
        ]

        self.buttons = []

        for id, img, label in btns:
            item = self.editor3d_toolbar.AddTool(id, label, img.bitmap,
                                                 img.disabled_bitmap,
                                                 aui.ITEM_RADIO)
            self.buttons.append(item)
            self.Bind(wx.EVT_MENU, self.on_tool, id=id)

        self.editor3d_toolbar.Realize()
        self.editor3d_toolbar_pane = (
            aui.AuiPaneInfo()
            .Floatable(True)
            .Top()
            .Gripper(True)
            .Resizable(True)
            .Movable(True)
            .Name('editor3d_toolbar')
            .CaptionVisible(False)
            .PaneBorder(True)
            .CloseButton(False)
            .MaximizeButton(False)
            .MinimizeButton(False)
            .PinButton(False)
            .DestroyOnClose(False)
            .Show()
            .ToolbarPane()
        )

        self.mainframe.manager.AddPane(self.editor3d_toolbar, self.editor3d_toolbar_pane)
        self.mainframe.manager.Update()

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_left_dclick)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_RIGHT_UP, self.on_right_up)
        self.Bind(wx.EVT_RIGHT_DCLICK, self.on_right_dclick)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.Bind(wx.EVT_KEY_UP, self.on_key_up)

        v_sizer = wx.BoxSizer(wx.VERTICAL)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        v_sizer.Add(h_sizer, 1, wx.EXPAND)
        self.SetSizer(v_sizer)

        def _do():
            self.buttons[0].SetState(aui.AUI_BUTTON_STATE_CHECKED)

            for value in self.axes._axis_map.values():  # NOQA
                value.set_ticks_position('both')
                value.set_label_position('both')
            self.canvas.draw()

        wx.CallAfter(_do)

    def on_size(self, evt):
        w, h = evt.GetSize()
        size_ = max(w, h)
        axes_off_x = utils.remap(size_, 474, 2333, -1.1, -1.60)
        axes_off_y = utils.remap(size_, 474, 2333, -1.1, -1.4)
        axes_size = utils.remap(size_, 474, 2333, 3.2, 4.20)

        self.axes.set_position([axes_off_x, axes_off_y, axes_size, axes_size])
        self.fig.canvas.draw_idle()
        evt.Skip()

    def on_tool(self, evt):
        self.mode = evt.GetId()

    def on_motion(self, evt: MouseEvent):
        evt.Skip()

    def on_left_down(self, evt: MouseEvent):
        evt.Skip()

    def on_left_up(self, evt: MouseEvent):
        evt.Skip()

    def on_left_dclick(self, evt: MouseEvent):
        evt.Skip()

    def on_right_down(self, evt: MouseEvent):
        evt.Skip()

    def on_right_up(self, evt: MouseEvent):
        artist = evt.GetArtist()
        x, y = evt.GetPosition()

        if artist is not None:
            obj = artist.get_py_data()
            obj.menu3d(self, x, y)

        evt.Skip()

    def on_right_dclick(self, evt: MouseEvent):
        evt.Skip()

    def on_key_down(self, evt: KeyEvent):
        evt.Skip()

    def on_key_up(self, evt: KeyEvent):
        evt.Skip()


