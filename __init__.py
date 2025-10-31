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
from mpl_toolkits.mplot3d import axes3d  # NOQA
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

        v_sizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.fig = matplotlib.pyplot.figure(figsize=(3.5, 3.5))
        ax = self.axes = axes3d.Axes3D(self.fig, [-0.80, -0.95, 2.8, 2.8], box_aspect=(1, 1, 1))

        self.fig.add_axes(ax)
        # ax.autoscale(True)

        ax.set_xlim(-50, 50)
        ax.set_ylim(-50, 50)
        ax.set_zlim(-50, 50)

        # get_tightbbox
        ax.set_adjustable('datalim')
        ax.set_aspect('equal', 'box')

        self.canvas = _canvas.Canvas(self.mainframe, self, wx.ID_ANY, self.fig, self.axes)

        inlay = self.inlay = axis_indicator.AxisIndicator(self.fig, [0.88, 0.02, 0.10, 0.10])
        ax.shareview(inlay)
        self.fig.add_axes(inlay)

        hsizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        v_sizer.Add(hsizer, 1, wx.EXPAND)

        self.SetSizer(v_sizer)

        self.Bind(wx.EVT_SIZE, self._on_panel_size)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_left_up)
        # self.Bind(wx.EVT_LEFT_DCLICK, self._on_left_dclick)
        self.Bind(wx.EVT_RIGHT_DOWN, self._on_right_down)
        self.Bind(wx.EVT_RIGHT_UP, self._on_right_up)
        # self.Bind(wx.EVT_RIGHT_DCLICK, self._on_right_dclick)
        # self.Bind(wx.EVT_MOUSEWHEEL, self._on_mouse_wheel)
        self.Bind(wx.EVT_KEY_UP, self._on_key_up)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

        self.transitions = []
        self.bundles = []
        self._selected = None
        self._mouse_click_location = None
        self.bundle_dialog = None
        self._right_motion = None
        self.canvas.draw()

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

        for id, img, label in btns:  # NOQA
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

        v_sizer = wx.BoxSizer(wx.VERTICAL)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        v_sizer.Add(h_sizer, 1, wx.EXPAND)
        self.SetSizer(v_sizer)

        def _do():
            self.buttons[0].SetState(aui.AUI_BUTTON_STATE_CHECKED)

        wx.CallAfter(_do)

    def _on_panel_size(self, evt):
        w, h = evt.GetSize()
        self.canvas.SetSize((w, h))
        size_ = max(w, h)
        axes_off_x = utils.remap(size_, 474, 2333, -1.1, -1.60)
        axes_off_y = utils.remap(size_, 474, 2333, -1.1, -1.4)
        axes_size = utils.remap(size_, 474, 2333, 3.2, 4.20)
        self.axes.set_position([axes_off_x, axes_off_y, axes_size, axes_size])
        self.fig.canvas.draw_idle()

        evt.Skip()

    def SetSelected(self, obj, flag):
        if not flag and self._selected == obj:
            self._selected.IsSelected(False)
            self._selected = None
        elif flag and self._selected is not None and self._selected != obj:
            self._selected.IsSelected(False)
            self._selected = obj
            self._selected.IsSelected(True)
        elif flag and self._selected is None:
            self._selected = obj
            self._selected.IsSelected(True)
        else:
            raise RuntimeError('sanity check')

    def _on_motion(self, evt: MouseEvent):
        if evt.RightIsDown():
            self._right_motion = True

        evt.Skip()

    def _on_left_down(self, evt: MouseEvent):  # NOQA
        evt.Skip()

    def _on_left_up(self, evt: MouseEvent):  # NOQA
        evt.Skip()

    ID_ADD_TRANSITION = wx.NewIdRef()
    ID_ADD_BUNDLE = wx.NewIdRef()

    def _on_right_down(self, evt: MouseEvent):
        self._right_motion = False
        evt.Skip()

    def _on_right_up(self, evt: MouseEvent):
        evt.Skip()

        if self._right_motion:
            self._right_motion = False
            return

        artist = evt.GetArtist()
        x, y = evt.GetPosition()

        if artist is None:
            menu = wx.Menu()
            menu.Append(self.ID_ADD_TRANSITION, "Add Transition")
            menu.Append(self.ID_ADD_BUNDLE, "Add Bundle")

            self._mouse_click_location = evt.GetPosition3D()

            self.PopupMenu(menu, x, y)
        else:
            pass
            # obj.menu(self, x, y)

    def _on_key_up(self, evt: KeyEvent):  # NOQA
        evt.Skip()

    def _on_key_down(self, evt: KeyEvent):  # NOQA
        evt.Skip()

    def on_tool(self, evt):
        self.mode = evt.GetId()
