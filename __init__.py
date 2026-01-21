from typing import TYPE_CHECKING

import wx

from wx import aui
from ..widgets import aui_toolbar

from .. import image as _image
from .canvas import canvas as _canvas

from ..geometry import point as _point
from ..wrappers.decimal import Decimal as _decimal

from . import part_3d_preview as _part3d_preview


if TYPE_CHECKING:
    from .. import ui as _ui


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

    ID_MOVE = wx.NewIdRef()
    ID_SET_ANGLE = wx.NewIdRef()

    def __init__(self, parent, mainframe: "_ui.MainFrame", size: tuple[int, int]):
        wx.Panel.__init__(self, parent, wx.ID_ANY, size=size, style=wx.BORDER_NONE)
        self.mainframe = mainframe
        w_size = size
        view_size = _canvas.Canvas.get_view_size()

        w, h = size
        size = _point.Point(_decimal(w), _decimal(h))
        pos = (size - view_size) / _decimal(2.0)

        self.mode = self.ID_POINTER

        self.global_db = self.mainframe.global_db

        self.transitions = []
        self.bundles = []
        self._selected = None
        self._mouse_click_location = None
        self.bundle_dialog = None
        self._right_motion = None

        self.editor3d_toolbar = aui_toolbar.AuiToolBar(self.mainframe,
                                                       style=aui.AUI_TB_GRIPPER | aui.AUI_TB_TEXT)

        self.editor3d_toolbar.SetToolBitmapSize((32, 32))

        pointer = _image.icons.pointer.resize(32, 32)
        transition = _image.icons.transition.resize(32, 32)
        connector = _image.icons.connector.resize(32, 32)
        terminal = _image.icons.terminal.resize(32, 32)
        seal = _image.icons.seal.resize(32, 32)
        wire = _image.icons.wire.resize(32, 32)
        splice = _image.icons.splice.resize(32, 32)
        bundle_cover = _image.icons.bundle_cover.resize(32, 32)
        tpa_lock = _image.icons.tpa_lock.resize(32, 32)
        cpa_lock = _image.icons.cpa_lock.resize(32, 32)

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
            item = self.editor3d_toolbar.AddTool(
                id, label, img.bitmap,
                img.disabled_bitmap,
                aui.ITEM_RADIO
                )
            self.buttons.append(item)
            self.Bind(wx.EVT_MENU, self.on_tool, id=id)

        # self.preview_pane = PreviewPane(self.mainframe)

        self.editor3d_toolbar.Realize()
        self.editor3d_toolbar_pane = (
            aui.AuiPaneInfo()
            .Floatable(True)
            .Top()
            .Gripper(True)
            .Resizable(True)
            .Movable(True)
            .Name('editor_toolbar')
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

        self.mainframe.manager.AddPane(self.editor3d_toolbar,
                                       self.editor3d_toolbar_pane)
        self.mainframe.manager.Update()

        # v_sizer = wx.BoxSizer(wx.VERTICAL)
        # h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # h_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        # v_sizer.Add(h_sizer, 1, wx.EXPAND)
        # self.SetSizer(v_sizer)

        self.objects = []

        def _do():
            self.buttons[0].SetState(aui.AUI_BUTTON_STATE_CHECKED)

        wx.CallAfter(_do)

        self.panel = wx.Panel(self, wx.ID_ANY,
                              size=view_size.as_int[:-1], pos=pos.as_int[:-1])

        self.canvas = _canvas.Canvas(self.panel, self.mainframe,
                                     size=view_size.as_int[:-1], pos=(0, 0))

        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

        w, h = w_size
        s = max([w, h])

        x = w
        y = h

        s //= 8

        x -= s
        y -= s + (s / 2)

        self.axis_overlay = _axis_indicators.Overlay(
            self, size=(int(s), int(s)), pos=(int(x), int(y)))

        self.Bind(wx.EVT_SIZE, self.on_size)

    def on_size(self, evt):
        x1, y1 = self.axis_overlay.GetPosition()
        w, h = self.axis_overlay.GetSize()

        x2 = x1 + w
        y2 = y1 + h

        w, h = evt.GetSize()

        if x1 < 0:
            x2 += -x1
            x1 = 0
        if y1 < 0:
            y2 += -y1
            y1 = 0

        if x2 > w:
            x1 += w - x2

        if y2 > h:
            y1 += h - y2

        self.axis_overlay.Move((x1, y1))
        evt.Skip()

    def on_erase_background(self, _):
        pass




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
