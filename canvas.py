import wx
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

from matplotlib.backend_bases import (ResizeEvent as _ResizeEvent,
                                      MouseEvent as _MouseEvent,
                                      KeyEvent as _KeyEvent,
                                      MouseButton as _MouseButton)

from ..wrappers.wxkey_event import KeyEvent
from ..wrappers.wxmouse_event import MouseEvent
from ..wrappers.wxartist_event import (ArtistEvent,
                                       wxEVT_COMMAND_ARTIST_SET_SELECTED,
                                       wxEVT_COMMAND_ARTIST_UNSET_SELECTED)
from ..wrappers.decimal import Decimal as _decimal
from ..geometry import point as _point


class Canvas(FigureCanvas):

    def __init__(self, editor, parent, id_, fig, axes):
        super().__init__(parent, id_, fig)
        self.axes = axes
        self.editor = editor

        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)

        self._key_code = wx.WXK_NONE
        self._raw_key_code = wx.WXK_NONE
        self._raw_key_flags = 0
        self._unicode_key = ''
        self._selected_artist = None
        self._tmp_selected_artist = None
        self._inlay_selected = None
        self._inlay_coords = None
        self._inlay_move = None
        self._inlay_corners = None
        self._inlay_corner_grab = 0
        self._scrap_first_move = True
        self._is_drag_event = False
        self.renderer = None

        self.mpl_connect("pick_event", self._on_pick)

    # bypass erasing the background when the plot is redrawn.
    # This helps to eliminate the flicker that is seen when a redraw occurs.
    # the second piece needed to eliminate the flicker is seen below
    def _on_erase_background(self, _):
        pass
    #
    # def draw(self, drawDC=None):
    #     """
    #     Render the figure using RendererWx instance renderer, or using a
    #     previously defined renderer if none is specified.
    #     """
    #
    #     # no need to recreate the renderer over and over
    #     # again when forcing a redraw
    #
    #     if self.renderer is None:
    #         self.renderer = RendererWx(self.bitmap, self.figure.dpi)
    #
    #     self.figure.draw(self.renderer)
    #     self._isDrawn = True
    #     self.gui_repaint(drawDC=drawDC)

    # override the _on_paint method in the canvas
    # this is done so double buffer is used which eliminates the flicker
    # that is seen when the plot redraws
    def _on_paint(self, event):
        drawDC = wx.BufferedPaintDC(self)
        if not self._isDrawn:
            self.draw(drawDC=drawDC)
        else:
            self.gui_repaint(drawDC=drawDC)

        if self._inlay_corners is not None:
            gcdc = wx.GCDC(drawDC)
            gcdc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 255), 2))
            gcdc.SetBrush(wx.TRANSPARENT_BRUSH)

            x1, y1 = self._inlay_corners[0]
            x2, y2 = self._inlay_corners[-1]
            w = x2 - x1 + 1
            h = y2 - y1 + 1
            gcdc.DrawRectangle(int(x1), int(y1), int(w), int(h))
            gcdc.Destroy()
            del gcdc

        drawDC.Destroy()
    #
    # def gui_repaint(self, drawDC=None):
    #     # The "if self" check avoids a "wrapped C/C++ object has been deleted"
    #     # RuntimeError if doing things after window is closed.
    #     if not (self and self.IsShownOnScreen()):
    #         return
    #
    #     if not drawDC:  # not called from OnPaint use a ClientDC
    #         drawDC = wx.ClientDC(self)
    #     # For 'WX' backend on Windows, the bitmap cannot be in use by another
    #     # DC (see GraphicsContextWx._cache).
    #     bmp = (self.bitmap.ConvertToImage().ConvertToBitmap()
    #            if wx.Platform == '__WXMSW__' and isinstance(self.figure.canvas.get_renderer(), RendererWx)
    #            else self.bitmap)
    #     drawDC.DrawBitmap(bmp, 0, 0)
    #     if self._rubberband_rect is not None:
    #         # Some versions of wx+python don't support numpy.float64 here.
    #         x0, y0, x1, y1 = map(round, self._rubberband_rect)
    #         rect = [(x0, y0, x1, y0), (x1, y0, x1, y1),
    #                 (x0, y0, x0, y1), (x0, y1, x1, y1)]
    #         drawDC.DrawLineList(rect, self._rubberband_pen_white)
    #         drawDC.DrawLineList(rect, self._rubberband_pen_black)
    #
    # def draw_idle(self):
    #     self._isDrawn = False  # Force redraw
    #     self.Refresh(eraseBackground=False)

    # override the _on_size method in the canvas
    def _on_size(self, event):
        self._update_device_pixel_ratio()
        sz = self.GetParent().GetSizer()
        if sz:
            si = sz.GetItem(self)
        else:
            si = None

        if sz and si and not si.Proportion and not si.Flag & wx.EXPAND:
            size = self.GetMinSize()
        else:
            size = self.GetClientSize()
            size.IncTo(self.GetMinSize())

        if getattr(self, "_width", None):
            if size == (self._width, self._height):
                return

        self._width, self._height = size
        self._isDrawn = False

        if self._width <= 1 or self._height <= 1:
            return

        dpival = self.figure.dpi

        if wx.Platform != '__WXMSW__':
            scale = self.GetDPIScaleFactor()
            dpival /= scale

        winch = self._width / dpival
        hinch = self._height / dpival
        self.figure.set_size_inches(winch, hinch, forward=False)

        self.Refresh(eraseBackground=False)
        _ResizeEvent("resize_event", self)._process()  # NOQA
        self.draw_idle()

    def _mpl_coords(self, pos=None):
        """
        Convert a wx position, defaulting to the current cursor position, to
        Matplotlib coordinates.
        """
        if pos is None:
            pos = wx.GetMouseState()
            x, y = self.ScreenToClient(pos.X, pos.Y)
        else:
            x, y = pos
        # flip y so y=0 is bottom of canvas
        if not wx.Platform == '__WXMSW__':
            scale = self.GetDPIScaleFactor()
            return x*scale, self.figure.bbox.height - y*scale
        else:
            return x, self.figure.bbox.height - y

    def world_coords(self, point=None) -> _point.Point:
        x, y = self._mpl_coords(point)

        xv, yv = self._get_inaxes(x, y)

        if None in (xv, yv):
            return None

        if not hasattr(self.axes, '_sx') or not hasattr(self.axes, '_sy'):
            self.axes._sx, self.axes._sy = xv, yv

        p1, pane_idx = self.axes._calc_coord(xv, yv, None)  # NOQA
        xs = self.axes.format_xdata(p1[0])
        ys = self.axes.format_ydata(p1[1])
        zs = self.axes.format_zdata(p1[2])

        def get_decimal(val):
            # this is not a minus sign tho it should be.
            if val.startswith('−'):
                val = val[1:].replace('−', '-')
                return _decimal(-float(val))
            # These are actually different.
            elif '−' in val:
                val = val.replace('−', '-')
                return _decimal(float(val))
            else:
                return _decimal(float(val))

        return _point.Point(get_decimal(xs), get_decimal(ys), z=get_decimal(zs))

    def _get_inaxes(self, x, y):
        inaxes = self.inaxes((x, y))

        if inaxes is not None:
            try:
                return inaxes.transData.inverted().transform((x, y))
            except ValueError:
                pass

        return None, None

    def _on_pick(self, evt):
        artist = evt.artist.get_py_data()

        x, y = self._mpl_coords()
        m_event = _MouseEvent("button_press_event", self, x, y, _MouseButton.LEFT,
                              modifiers=[], guiEvent=None)

        if self._selected_artist == artist:
            self._tmp_selected_artist = self._selected_artist
            return

        if self._selected_artist is not None:
            e = ArtistEvent(wxEVT_COMMAND_ARTIST_UNSET_SELECTED, self._selected_artist.wxid)
            e.SetEventObject(self)
            e.SetArtist(self._selected_artist)
            e.SetPosition3D(self.world_coords())
            e.SetMatplotlibEvent(m_event)
            self._selected_artist = None
            self.GetParent().ProcessEvent(e)

        self._tmp_selected_artist = artist
        e = ArtistEvent(wxEVT_COMMAND_ARTIST_SET_SELECTED, artist.wxid)
        e.SetEventObject(self)
        e.SetArtist(artist)
        e.SetPosition3D(self.world_coords())
        e.SetMatplotlibEvent(m_event)
        m_state = wx.GetMouseState()
        e.SetPosition(self.ScreenToClient(m_state.GetPosition()))
        self.GetParent().ProcessEvent(e)

    def _on_key_down(self, event: wx.KeyEvent):
        event.StopPropagation()

        self._key_code = event.GetKeyCode()
        self._raw_key_code = event.GetRawKeyCode()
        self._raw_key_flags = event.GetRawKeyFlags()

        e = KeyEvent(wx.wxEVT_KEY_DOWN)
        e.SetShiftDown(event.ShiftDown())
        e.SetAltDown(event.AltDown())
        e.SetControlDown(event.ControlDown())
        e.SetKeyCode(event.GetKeyCode())

        if event.GetUnicodeKey():
            self._unicode_key = chr(event.GetUnicodeKey())

            if not event.ShiftDown():
                self._unicode_key = self._unicode_key.lower()

            e.SetUnicodeKey(self._unicode_key)
        else:
            self._unicode_key = None

        e.SetPosition3D(self.world_coords(event.GetPosition()))
        e.SetPosition(event.GetPosition())
        e.SetEventObject(event.GetEventObject())
        e.SetMetaDown(event.MetaDown())
        e.SetRawControlDown(event.ControlDown())
        e.SetRawKeyCode(event.GetRawKeyCode())
        e.SetRawKeyFlags(event.GetRawKeyFlags())
        e.SetRefData(event.GetRefData())
        e.SetArtist(self._selected_artist)
        e.SetId(event.GetId())
        m_event = _KeyEvent("key_press_event", self, self._get_key(event),
                            *self._mpl_coords(event.GetPosition()), guiEvent=event)
        e.SetMatplotlibEvent(m_event)
        self.GetParent().ProcessEvent(e)

        m_event._process()  # NOQA

    def _on_key_up(self, event):
        event.StopPropagation()

        self._key_code = None
        self._raw_key_code = None
        self._raw_key_flags = None
        self._unicode_key = None

        e = KeyEvent(wx.wxEVT_KEY_UP)
        e.SetShiftDown(event.ShiftDown())
        e.SetAltDown(event.AltDown())
        e.SetControlDown(event.ControlDown())
        e.SetKeyCode(event.GetKeyCode())

        if event.GetUnicodeKey():
            unicode_key = chr(event.GetUnicodeKey())

            if not event.ShiftDown():
                unicode_key = unicode_key.lower()

            e.SetUnicodeKey(unicode_key)

        e.SetPosition3D(self.world_coords(event.GetPosition()))
        e.SetPosition(event.GetPosition())
        e.SetEventObject(event.GetEventObject())
        e.SetMetaDown(event.MetaDown())
        e.SetRawControlDown(event.ControlDown())
        e.SetRawKeyCode(event.GetRawKeyCode())
        e.SetRawKeyFlags(event.GetRawKeyFlags())
        e.SetRefData(event.GetRefData())
        e.SetArtist(self._selected_artist)
        e.SetId(event.GetId())

        m_event = _KeyEvent("key_release_event", self, self._get_key(event),
                            *self._mpl_coords(event.GetPosition()), guiEvent=event)
        e.SetMatplotlibEvent(m_event)
        self.GetParent().ProcessEvent(e)

        m_event._process()  # NOQA

    def _on_mouse_button(self, event: wx.MouseEvent):
        event.StopPropagation()
        if self.HasCapture():
            self.ReleaseMouse()

        x, y = self._mpl_coords(event.GetPosition())
        button_map = {
            wx.MOUSE_BTN_LEFT: _MouseButton.LEFT,
            wx.MOUSE_BTN_MIDDLE: _MouseButton.MIDDLE,
            wx.MOUSE_BTN_RIGHT: _MouseButton.RIGHT,
            wx.MOUSE_BTN_AUX1: _MouseButton.BACK,
            wx.MOUSE_BTN_AUX2: _MouseButton.FORWARD,
        }
        button = event.GetButton()
        modifiers = self._mpl_modifiers(event)

        if event.ButtonDClick():
            e_text = 'button_press_event'
        elif event.ButtonDown():
            e_text = 'button_press_event'
        else:
            e_text = 'button_release_event'

        if event.ButtonDClick():
            if button == wx.MOUSE_BTN_LEFT:
                m_event = _MouseEvent(e_text, self, x, y,
                                      button_map.get(button, button),
                                      modifiers=modifiers, guiEvent=event)
            else:
                m_event = _MouseEvent(e_text, self, x, y,
                                      button_map.get(button, button),
                                      dblclick=True, modifiers=modifiers, guiEvent=event)

        else:
            m_event = _MouseEvent(e_text, self, x, y,
                                  button_map.get(button, button),
                                  modifiers=modifiers, guiEvent=event)

        if button == wx.MOUSE_BTN_LEFT:
            if event.ButtonDClick():
                m_event._process()  # NOQA

                if self._tmp_selected_artist:
                    if self._tmp_selected_artist == self._selected_artist:
                        # do double click event for artist
                        pass
                    else:
                        self._selected_artist = self._tmp_selected_artist

                    self._tmp_selected_artist = None
                elif self._selected_artist is not None:
                    e = ArtistEvent(wxEVT_COMMAND_ARTIST_UNSET_SELECTED,
                                    self._selected_artist.wxid)
                    e.SetEventObject(self)
                    e.SetArtist(self._selected_artist)
                    e.SetPosition3D(self.world_coords())
                    self._selected_artist = None
                    self.GetParent().ProcessEvent(e)

                e = MouseEvent(wx.wxEVT_LEFT_DCLICK)
            elif event.ButtonDown():
                mx, my = event.GetPosition()
                if self._inlay_corners is None:
                    bbox = self.editor.inlay.get_position()
                    w, h = self.GetSize()

                    bounds = bbox.bounds
                    x1, y1, inlay_w, inlay_h = [value[0] * value[1]
                                                for value in zip(bounds, [w, h, w, h])]

                    if not wx.Platform == '__WXMSW__':
                        scale = self.GetDPIScaleFactor()
                        y1 *= scale
                        y1 = h - y1 * scale
                        y1 -= inlay_h
                    else:
                        y1 = h - y1 - inlay_h

                    x2 = inlay_w + x1
                    y2 = inlay_h + y1
                else:
                    x1, y1 = self._inlay_corners[0]
                    x2, y2 = self._inlay_corners[-1]

                if self._inlay_selected is None:
                    if x1 <= mx <= x2 and y1 <= my <= y2:
                        self._inlay_move = [mx, my]
                        self._inlay_selected = self.editor.inlay
                        self._inlay_corner_grab = 5
                        self._inlay_corners = [[x1, y1], [x2, y1], [x1, y2], [x2, y2]]
                        self._scrap_first_move = True
                        self.axes.get_figure(root=True).canvas.draw_idle()
                        return
                else:
                    inlay_corners = [[x1, y1], [x2, y1], [x1, y2], [x2, y2]]

                    for i, p in enumerate(inlay_corners):
                        px1 = p[0] - 5
                        py1 = p[1] - 5
                        px2 = p[0] + 5
                        py2 = p[1] + 5

                        if px1 <= mx <= px2 and py1 <= my <= py2:
                            self._inlay_corner_grab = i + 1
                            self._inlay_corners = inlay_corners
                            self._scrap_first_move = True
                            self._inlay_move = [mx, my]
                            self.CaptureMouse()
                            return

                    if x1 <= mx <= x2 and y1 <= my <= y2:
                        self._inlay_corner_grab = 5
                        self._inlay_move = [mx, my]
                        self.CaptureMouse()
                        return
                    elif self._inlay_corners is not None:
                        self._inlay_move = None
                        self._inlay_selected = None
                        self._inlay_corners = None
                        self._inlay_corner_grab = 0
                        self.axes.get_figure(root=True).canvas.draw_idle()

                m_event._process()  # NOQA

                if self._tmp_selected_artist:
                    self._selected_artist = self._tmp_selected_artist
                    self._tmp_selected_artist = None
                    self._is_drag_event = True
                    self.CaptureMouse()

                elif self._selected_artist is not None:
                    e = ArtistEvent(wxEVT_COMMAND_ARTIST_UNSET_SELECTED,
                                    self._selected_artist.wxid)
                    e.SetEventObject(self)
                    e.SetArtist(self._selected_artist)
                    e.SetPosition3D(self.world_coords())
                    self._selected_artist = None
                    self.GetParent().ProcessEvent(e)

                e = MouseEvent(wx.wxEVT_LEFT_DOWN)
            elif event.ButtonUp():
                if self._inlay_move is not None:
                    self._inlay_move = None
                    self._inlay_corner_grab = 0
                    return

                self._is_drag_event = False
                e = MouseEvent(wx.wxEVT_LEFT_UP)
            else:
                return

        elif button == wx.MOUSE_BTN_MIDDLE:
            if event.ButtonDown():
                e = MouseEvent(wx.wxEVT_MIDDLE_DOWN)
            elif event.ButtonDClick():
                e = MouseEvent(wx.wxEVT_MIDDLE_DCLICK)
            elif event.ButtonUp():
                e = MouseEvent(wx.wxEVT_MIDDLE_UP)
            else:
                return
        elif button == wx.MOUSE_BTN_RIGHT:
            if event.ButtonDown():
                e = MouseEvent(wx.wxEVT_RIGHT_DOWN)
            elif event.ButtonDClick():
                e = MouseEvent(wx.wxEVT_RIGHT_DCLICK)
            elif event.ButtonUp():
                e = MouseEvent(wx.wxEVT_RIGHT_UP)
            else:
                return
        elif button == wx.MOUSE_BTN_AUX1:
            if event.ButtonDown():
                e = MouseEvent(wx.wxEVT_AUX1_DOWN)
            elif event.ButtonDClick():
                e = MouseEvent(wx.wxEVT_AUX1_DCLICK)
            elif event.ButtonUp():
                e = MouseEvent(wx.wxEVT_AUX1_UP)
            else:
                return
        elif button == wx.MOUSE_BTN_AUX2:
            if event.ButtonDown():
                e = MouseEvent(wx.wxEVT_AUX2_DOWN)
            elif event.ButtonDClick():
                e = MouseEvent(wx.wxEVT_AUX2_DCLICK)
            elif event.ButtonUp():
                e = MouseEvent(wx.wxEVT_AUX2_UP)
            else:
                return
        else:
            return

        e.SetAltDown(event.AltDown())
        e.SetAux1Down(event.Aux1Down())
        e.SetAux2Down(event.Aux2Down())
        e.SetColumnsPerAction(event.GetColumnsPerAction())
        e.SetControlDown(event.ControlDown())
        e.SetEventObject(event.GetEventObject())
        e.SetEventType(event.GetEventType())
        e.SetLeftDown(event.LeftDown())
        e.SetLinesPerAction(event.GetLinesPerAction())
        e.SetMetaDown(event.MetaDown())
        e.SetMiddleDown(event.MiddleDown())
        e.SetPosition3D(self.world_coords(event.GetPosition()))
        e.SetPosition(event.GetPosition())
        e.SetRawControlDown(event.RawControlDown())
        e.SetRefData(event.GetRefData())
        e.SetRightDown(event.RightDown())
        e.SetShiftDown(event.ShiftDown())
        e.SetTimestamp(event.GetTimestamp())
        e.SetWheelAxis(event.GetWheelAxis())
        e.SetWheelDelta(event.GetWheelDelta())
        e.SetWheelRotation(event.GetWheelRotation())
        e.SetArtist(self._selected_artist)
        e.SetMatplotlibEvent(m_event)

        if self._selected_artist is None:
            e.SetId(event.GetId())
        else:
            e.SetId(self._selected_artist.wxid)

        if self._key_code:
            e.SetKeyCode(self._key_code)

        if self._raw_key_code:
            e.SetRawKeyCode(self._raw_key_code)

        if self._raw_key_flags:
            e.SetRawKeyFlags(self._raw_key_flags)

        if self._unicode_key:
            e.SetUnicodeKey(self._unicode_key)

        self.GetParent().ProcessEvent(e)

        if (
            not (event.ButtonDClick() and button == wx.MOUSE_BTN_LEFT) and
            not (event.ButtonDown() and button == wx.MOUSE_BTN_LEFT)
        ):
            m_event._process()  # NOQA

    def _on_mouse_wheel(self, event):
        event.StopPropagation()

        x, y = self._mpl_coords(event.GetPosition())
        # Convert delta/rotation/rate into a floating point step size
        step = event.LinesPerAction * event.WheelRotation / event.WheelDelta
        # Mac gives two events for every wheel event; skip every second one.
        if wx.Platform == '__WXMAC__':
            if not hasattr(self, '_skipwheelevent'):
                self._skipwheelevent = True
            elif self._skipwheelevent:
                self._skipwheelevent = False
                return  # Return without processing event
            else:
                self._skipwheelevent = True

        e = MouseEvent(wx.wxEVT_MOUSEWHEEL)
        e.SetAltDown(event.AltDown())
        e.SetAux1Down(event.Aux1Down())
        e.SetAux2Down(event.Aux2Down())
        e.SetColumnsPerAction(event.GetColumnsPerAction())
        e.SetControlDown(event.ControlDown())
        e.SetEventObject(event.GetEventObject())
        e.SetEventType(event.GetEventType())
        e.SetLeftDown(event.LeftDown())
        e.SetLinesPerAction(event.GetLinesPerAction())
        e.SetMetaDown(event.MetaDown())
        e.SetMiddleDown(event.MiddleDown())
        e.SetPosition3D(self.world_coords(event.GetPosition()))
        e.SetPosition(event.GetPosition())
        e.SetRawControlDown(event.RawControlDown())
        e.SetRefData(event.GetRefData())
        e.SetRightDown(event.RightDown())
        e.SetShiftDown(event.ShiftDown())
        e.SetTimestamp(event.GetTimestamp())
        e.SetWheelAxis(event.GetWheelAxis())
        e.SetWheelDelta(event.GetWheelDelta())
        e.SetWheelRotation(event.GetWheelRotation())
        e.SetArtist(self._selected_artist)

        if self._selected_artist is None:
            e.SetId(event.GetId())
        else:
            e.SetId(self._selected_artist.wxid)

        if self._key_code:
            e.SetKeyCode(self._key_code)

        if self._raw_key_code:
            e.SetRawKeyCode(self._raw_key_code)

        if self._raw_key_flags:
            e.SetRawKeyFlags(self._raw_key_flags)

        if self._unicode_key:
            e.SetUnicodeKey(self._unicode_key)

        m_event = _MouseEvent("scroll_event", self, x, y, step=step,  # NOQA
                              modifiers=self._mpl_modifiers(event),
                              guiEvent=event)

        e.SetMatplotlibEvent(m_event)

        if (
            not event.ControlDown() and not event.RawControlDown() and
            not event.AltDown() and not event.MetaDown()
        ):
            h = min(self.axes._pseudo_h, self.axes._pseudo_w)  # NOQA

            scale = h / (h + (step / 100))
            self.axes._scale_axis_limits(scale, scale, scale)  # NOQA

            self.axes.get_figure(root=True).canvas.draw_idle()

            self.GetParent().ProcessEvent(e)
        else:
            self.GetParent().ProcessEvent(e)

            m_event._process()  # NOQA

    def _wx_coords(self, x, y):
        pw, ph = self.GetParent().GetSize()
        w, h = self.GetSize()

        offset_x = (pw - w) // 2
        offset_y = (ph - h) // 2

        return x + offset_x, y + offset_y

    def _on_motion(self, event):
        event.StopPropagation()

        if self._inlay_selected and event.LeftIsDown():
            self._is_drag_event = False

            if self._inlay_move is not None:
                last_x, last_y = self._inlay_move
                new_x, new_y = event.GetPosition()

                if self._scrap_first_move:
                    self._scrap_first_move = False
                    self._inlay_move = [new_x, new_y]
                    return

                x_diff = new_x - last_x
                y_diff = new_y - last_y
                self._inlay_move = [new_x, new_y]

                inlay_corners = self._inlay_corners[:]

                if self._inlay_corner_grab == 1:
                    inlay_corners[0][0] += int(x_diff)
                    inlay_corners[0][1] += int(y_diff)
                    inlay_corners[1][1] += int(y_diff)
                    inlay_corners[2][0] += int(x_diff)
                elif self._inlay_corner_grab == 2:
                    inlay_corners[1][0] += int(x_diff)
                    inlay_corners[1][1] += int(y_diff)
                    inlay_corners[0][1] += int(y_diff)
                    inlay_corners[3][0] += int(x_diff)
                elif self._inlay_corner_grab == 3:
                    inlay_corners[2][0] += int(x_diff)
                    inlay_corners[2][1] += int(y_diff)
                    inlay_corners[3][1] += int(y_diff)
                    inlay_corners[0][0] += int(x_diff)
                elif self._inlay_corner_grab == 4:
                    inlay_corners[3][0] += int(x_diff)
                    inlay_corners[3][1] += int(y_diff)
                    inlay_corners[2][1] += int(y_diff)
                    inlay_corners[1][0] += int(x_diff)
                elif self._inlay_corner_grab == 5:
                    for i in range(4):
                        inlay_corners[i][0] += int(x_diff)
                        inlay_corners[i][1] += int(y_diff)

                x1, y1 = inlay_corners[0]
                x2, y2 = inlay_corners[-1]
                inlay_w = x2 - x1 + 1
                inlay_h = y2 - y1 + 1

                if inlay_w < 30 or inlay_h < 30:
                    return

                self._inlay_corners = inlay_corners[:]

                w, h = self.GetSize()

                if not wx.Platform == '__WXMSW__':
                    scale = self.GetDPIScaleFactor()
                    inlay_y = (h + x1) / scale
                    inlay_y /= scale
                    inlay_y += inlay_h
                else:
                    inlay_y = h - y1 - inlay_h

                xscalar = x1 / w
                yscalar = inlay_y / h
                wscalar = inlay_w / w
                hscalar = inlay_h / h

                self.editor.inlay.set_position([xscalar, yscalar, wscalar, hscalar])
                self.axes.get_figure(root=True).canvas.draw_idle()
            return

        if (
            event.RightIsDown() and
            not event.ControlDown() and not event.RawControlDown() and
            not event.AltDown() and not event.MetaDown() and
            not event.Aux1IsDown() and not event.Aux2IsDown() and
            not event.LeftIsDown() and not event.MiddleIsDown()
        ):
            self.axes.button_pressed = None
            x, y = self._mpl_coords()

            px, py = self.axes.transData.transform([self.axes._sx, self.axes._sy])  # NOQA
            self.axes.start_pan(px, py, 2)
            # pan view (takes pixel coordinate input)
            self.axes.drag_pan(2, None, x, y)
            self.axes.end_pan()

            self.axes._sx, self.axes._sy = self._get_inaxes(x, y)
            # Always request a draw update at the end of interaction
            self.axes.get_figure(root=True).canvas.draw_idle()
            self._is_drag_event = False

        e = MouseEvent(wx.wxEVT_MOTION)
        e.SetAltDown(event.AltDown())
        e.SetAux1Down(event.Aux1IsDown())
        e.SetAux2Down(event.Aux2IsDown())
        e.SetColumnsPerAction(event.GetColumnsPerAction())
        e.SetControlDown(event.ControlDown())
        e.SetEventObject(event.GetEventObject())
        e.SetLeftDown(event.LeftIsDown())
        e.SetLinesPerAction(event.GetLinesPerAction())
        e.SetMetaDown(event.MetaDown())
        e.SetMiddleDown(event.MiddleIsDown())
        e.SetPosition3D(self.world_coords(event.GetPosition()))
        e.SetPosition(event.GetPosition())
        e.SetRawControlDown(event.RawControlDown())
        e.SetRefData(event.GetRefData())
        e.SetRightDown(event.RightIsDown())
        e.SetShiftDown(event.ShiftDown())
        e.SetTimestamp(event.GetTimestamp())
        e.SetWheelAxis(event.GetWheelAxis())
        e.SetWheelDelta(event.GetWheelDelta())
        e.SetWheelRotation(event.GetWheelRotation())

        if self._selected_artist is not None:
            e.SetArtist(self._selected_artist)

        if self._key_code:
            e.SetKeyCode(self._key_code)

        if self._raw_key_code:
            e.SetRawKeyCode(self._raw_key_code)

        if self._raw_key_flags:
            e.SetRawKeyFlags(self._raw_key_flags)

        if self._unicode_key:
            e.SetUnicodeKey(self._unicode_key)

        e.SetId(self.GetId())

        m_event = _MouseEvent("motion_notify_event", self, *self._mpl_coords(event.GetPosition()),
                              buttons=self._mpl_buttons(), modifiers=self._mpl_modifiers(event),
                              guiEvent=event)

        e.SetMatplotlibEvent(m_event)

        if self.HasCapture() and event.LeftIsDown():
            if self._selected_artist is not None:
                self._selected_artist.on_motion(e)
                return
            else:
                self._is_drag_event = True

        else:
            self._is_drag_event = False

        m_event._process()  # NOQA

        self.GetParent().ProcessEvent(e)

    def _on_enter(self, event):
        """Mouse has entered the window."""
        event.Skip()
        # LocationEvent("figure_enter_event", self,
        #               *self._mpl_coords(event.GetPosition()),
        #               modifiers=self._mpl_modifiers(),
        #               guiEvent=event)._process()

    def _on_leave(self, event):
        """Mouse has left the window."""
        event.Skip()
        # LocationEvent("figure_leave_event", self,
        #               *self._mpl_coords(event.GetPosition()),
        #               modifiers=self._mpl_modifiers(),
        #               guiEvent=event)._process()

    def _set_capture(self, capture=True):
        pass

    def _on_capture_lost(self, event):
        if self.HasCapture():
            self.ReleaseMouse()

        event.Skip()
