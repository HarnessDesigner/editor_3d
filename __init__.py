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

from ..wrappers import art3d as _

from mpl_toolkits.mplot3d.art3d import Line3D, Path3DCollection
from decimal import Decimal as decimal  # NOQA

import matplotlib.pyplot  # NOQA
import numpy as np  # NOQA

from wx.lib.agw import aui
from ..widgets import aui_toolbar
from .. import image as _image

from . import canvas as _canvas


if TYPE_CHECKING:
    from .. import ui


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
        self.key = None
        self.selected_object = None
        self.button_held = False
        self.had_motion = False
        self.object_tooltip = None
        self._offset = None
        self.data = None
        self.mode = self.ID_POINTER

        self.mainframe: "ui.MainFrame" = parent.GetParent()
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        v_sizer = wx.BoxSizer(wx.VERTICAL)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.fig = matplotlib.pyplot.figure()

        ax = self.axes = self.fig.add_subplot(projection='3d')
        ax.autoscale(True)

        # Set the axis labels
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_zlabel('z')

        self.canvas = _canvas.Canvas(self, wx.ID_ANY, self.fig)

        # MouseEvent
        self.canvas.mpl_connect("button_press_event", self.on_press)
        self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.canvas.mpl_connect("button_release_event", self.on_release)
        self.canvas.mpl_connect("scroll_event", self.on_mouse_scroll)

        # LocationEvent
        self.canvas.mpl_connect("figure_enter_event", self.on_figure_enter)
        self.canvas.mpl_connect("figure_leave_event", self.on_figure_leave)
        self.canvas.mpl_connect("axes_enter_event", self.on_axes_enter)
        self.canvas.mpl_connect("axes_leave_event", self.on_axes_leave)

        # KeyEvent
        self.canvas.mpl_connect("key_press_event", self.on_key_press)
        self.canvas.mpl_connect("key_release_event", self.on_key_release)

        # CloseEvent
        self.canvas.mpl_connect("close_event", self.on_close)

        # DrawEvent
        self.canvas.mpl_connect("draw_event", self.on_draw)

        # PickEvent
        self.canvas.mpl_connect("pick_event", self.on_pick)

        # ResizeEvent
        self.canvas.mpl_connect("resize_event", self.on_resize)

        # toolbar = NavigationToolbar2WxAgg(self.canvas)
        # toolbar.Realize()

        h_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        v_sizer.Add(h_sizer, 1, wx.EXPAND)
        # v_sizer.Add(toolbar, 0, wx.LEFT | wx.EXPAND)

        self.SetSizer(v_sizer)
        # toolbar.update()

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

        #
        # self.editor3d_toolbar.AddTool(ID_TRANSITION, 'Add Transition', transition.bitmap, transition.disabled_bitmap, wx.ITEM_RADIO, '', '', None)
        # self.editor3d_toolbar.AddTool(ID_CONNECTOR, 'Add Connector', connector.bitmap, connector.disabled_bitmap, wx.ITEM_RADIO, '', '', None)
        # self.editor3d_toolbar.AddTool(ID_TERMINAL, 'Add Terminal', terminal.bitmap, terminal.disabled_bitmap, wx.ITEM_RADIO, '', '', None)
        # self.editor3d_toolbar.AddTool(ID_SEAL, 'Add Seal', seal.bitmap, seal.disabled_bitmap, wx.ITEM_RADIO, '', '', None)
        # self.editor3d_toolbar.AddTool(ID_WIRE, 'Add Wire', wire.bitmap, wire.disabled_bitmap, wx.ITEM_RADIO, '', '', None)
        # self.editor3d_toolbar.AddTool(ID_SPLICE, 'Add Splice', splice.bitmap, splice.disabled_bitmap, wx.ITEM_RADIO, '', '', None)
        # self.editor3d_toolbar.AddTool(ID_BUNDLE_COVER, 'Add Bundle', bundle_cover.bitmap, bundle_cover.disabled_bitmap, wx.ITEM_RADIO, '', '', None)
        # self.editor3d_toolbar.AddTool(ID_TPA_LOCK, 'Add TPA', tpa_lock.bitmap, tpa_lock.disabled_bitmap, wx.ITEM_RADIO, '', '', None)
        # self.editor3d_toolbar.AddTool(ID_CPA_LOCK, 'Add CPA', cpa_lock.bitmap, tpa_lock.disabled_bitmap, wx.ITEM_RADIO, '', '', None)
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

        def _do():
            self.buttons[0].SetState(aui.AUI_BUTTON_STATE_CHECKED)

            for value in self.axes._axis_map.values():  # NOQA
                value.set_ticks_position('both')
                value.set_label_position('both')
            self.canvas.draw()

        wx.CallAfter(_do)

    def on_tool(self, evt):
        self.mode = evt.GetId()

    def on_close(self, evt):
        pass

    def on_draw(self, evt):
        pass

    def on_key_press(self, evt):
        key = evt.key
        if isinstance(key, str):
            self.key = key.lower()

    def on_key_release(self, evt):
        key = evt.key
        if isinstance(key, str) and key.lower() == self.key:
            self.key = None

    def on_pick(self, evt):
        if isinstance(evt.artist, Path3DCollection):
            self.selected_object = evt.artist.get_py_data()
            self.axes.button_pressed = None

    def on_resize(self, evt):
        pass

    def on_mouse_scroll(self, evt):
        x, y = evt.xdata, evt.ydata

        if x is None or evt.inaxes != self.axes:
            return

        if not hasattr(self.axes, '_sx') or not hasattr(self.axes, '_sy'):
            self.axes._sx, self.axes._sy = x, y

        h = self.axes._pseudo_h  # NOQA

        scale = h / (h + (evt.step / 100))
        self.axes._scale_axis_limits(scale, scale, scale)  # NOQA

        self.axes.get_figure(root=True).canvas.draw_idle()

    def on_figure_enter(self, evt):
        pass

    def on_figure_leave(self, evt):
        pass

    def on_axes_enter(self, evt):
        pass

    def on_axes_leave(self, evt):
        pass

    def on_press(self, event):
        if event.button == 1:
            # left button
            if event.dblclick:
                pass
            elif self.selected_object is not None:
                self.button_held = True
                self.axes.button_pressed = None

        elif event.button == 2:
            # middle button
            pass
        elif event.button == 3:
            # right button
            # open context menu
            self.had_motion = False

        elif event.button == 8:
            # forward
            pass
        elif event.button == 9:
            # back
            pass

    def location_coords(self, xv, yv):
        p1, pane_idx = self.axes._calc_coord(xv, yv, None)  # NOQA
        xs = self.axes.format_xdata(p1[0])
        ys = self.axes.format_ydata(p1[1])
        zs = self.axes.format_zdata(p1[2])

        def get_decimal(val):
            if val.startswith('−'):
                return decimal(str(-float(val[1:])))
            else:
                return decimal(str(float(val)))

        return get_decimal(xs), get_decimal(ys), get_decimal(zs)

    def on_motion(self, event):
        if event.button == 3:
            self.had_motion = True
            # Start the pan event with pixel coordinates

            x, y = event.xdata, event.ydata
            # In case the mouse is out of bounds.
            if x is None or event.inaxes != self:
                return

            self.axes.button_pressed = None

            if not hasattr(self.axes, '_sx') or not hasattr(self.axes, '_sy'):
                self.axes._sx, self.axes._sy = event.xdata, event.ydata

            px, py = self.axes.transData.transform([self.axes._sx, self.axes._sy])  # NOQA
            self.axes.start_pan(px, py, 2)
            # pan view (takes pixel coordinate input)
            self.axes.drag_pan(2, None, event.x, event.y)
            self.axes.end_pan()

            self.axes._sx, self.axes._sy = event.xdata, event.ydata
            # Always request a draw update at the end of interaction
            self.axes.get_figure(root=True).canvas.draw_idle()

        elif self.button_held and self.selected_object is not None:
            if self.key not in ('x', 'y', 'z'):
                return

            try:
                x, y, z = self.location_coords(event.xdata, event.ydata)
            except TypeError:
                return

            old_pos = self.selected_object.center

            old_x, old_y, old_z = tuple(old_pos)

            if self._offset is None:
                if self.key == 'x':
                    self._offset = old_x - x
                elif self.key == 'y':
                    self._offset = old_y - y
                else:  # 'z'
                    self._offset = old_z - z

                return

            if self.key == 'x':
                x += self._offset
                old_pos.x = x
            elif self.key == 'y':
                y += self._offset
                old_pos.y = y
            elif self.key == 'z':
                z += self._offset
                old_pos.z = z


            self.axes.get_figure(root=True).canvas.draw_idle()

            height = self.canvas.GetSize()[1]
            x = round(x, 2)
            y = round(y, 2)
            z = round(z, 2)
            label = f'x: {x} y: {y} z: {z}'

            size = self.canvas.GetTextExtent(label)
            if self.object_tooltip is None:
                self.object_tooltip = wx.StaticText(self.canvas, wx.ID_ANY,
                                                    label=label, size=size,
                                                    pos=(0, height - size[1]))
            else:
                self.object_tooltip.SetLabel(label)
                self.object_tooltip.SetPosition((0, height - size[1]))
                self.object_tooltip.SetSize(size)

    def on_release(self, event):
        if self.object_tooltip is not None:
            self.object_tooltip.Destroy()
            self.object_tooltip = None
            self._offset = None

        if event.button == 3 and not self.had_motion:

            if self.selected_object is not None:
                menu = self.selected_object.actions_menu(self)

            else:
                menu = wx.Menu()
                wx.MenuItem()

                menu.Append(wx.ID_ANY, 'Add Connector')
                menu.Append(wx.ID_ANY, '')
                menu.Append(wx.ID_ANY, 'menu item 3')
                menu.AppendSeparator()
                menu.Append(wx.ID_ANY, 'menu item 4')
                menu.Append(wx.ID_ANY, 'menu item 5')
                menu.AppendSeparator()

                sub_menu = wx.Menu()
                sub_menu.Append(wx.ID_ANY, 'sub menu item 1')
                sub_menu.Append(wx.ID_ANY, 'sub menu item 2')
                sub_menu.Append(wx.ID_ANY, 'sub menu item 3')
                sub_menu.AppendSeparator()
                sub_menu.Append(wx.ID_ANY, 'sub menu item 4')
                sub_menu.Append(wx.ID_ANY, 'sub menu item 5')

                menu.AppendSubMenu(sub_menu, 'menu item 6')

            x = event.x
            y = event.y

            height = self.canvas.GetSize()[1]

            y = abs(y - height)

            self.canvas.PopupMenu(menu, x, y)
        else:
            self.selected_object = None
            self.button_held = False

        self.had_motion = False
