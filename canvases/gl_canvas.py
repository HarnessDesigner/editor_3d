
import wx
import math
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from wx import glcanvas

from ...wrappers.wxkey_event import KeyEvent
from ...wrappers.wxmouse_event import MouseEvent
from ...wrappers.wxartist_event import (ArtistEvent,
                                       wxEVT_COMMAND_ARTIST_SET_SELECTED,
                                       wxEVT_COMMAND_ARTIST_UNSET_SELECTED)
from ...wrappers.decimal import Decimal as _decimal
from ...geometry import point as _point


from . import CanvasBase, CanvasMeta


class GLCanvasMeta(type(glcanvas.GLCanvas), CanvasMeta):
    pass


class GLCanvas(glcanvas.GLCanvas, CanvasBase, metaclass=GLCanvasMeta):

    def __init__(self, parent, renderer):
        CanvasBase.__init__(self, parent, renderer)
        glcanvas.GLCanvas.__init__(self, parent, wx.ID_ANY)
        self.update_objects = True
        self.init = False
        self.context = glcanvas.GLContext(self)

        self.last_left_x = 0
        self.last_left_y = 0
        self.last_right_x = 0
        self.last_right_y = 0

        self.size = None
        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)
        self.Bind(wx.EVT_SIZE, self._on_size)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_mouse_down)
        self.Bind(wx.EVT_RIGHT_DOWN, self._on_mouse_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_mouse_up)
        self.Bind(wx.EVT_RIGHT_UP, self._on_mouse_up)
        self.Bind(wx.EVT_MOTION, self._on_mouse_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self._on_mouse_wheel)

        self._key_code = wx.WXK_NONE
        self._raw_key_code = wx.WXK_NONE
        self._raw_key_flags = 0
        self._unicode_key = ''
        self._selected_artist = None
        self._tmp_selected_artist = None
        self._is_drag_event = False
        self._grid = None

    def draw_grid(self, size=200.0, step=1.0, fade_dist=60.0):
        if self._grid is None:
            self._grid = []

            y = getattr(self, 'min_y', 0.0) - 1e-3
            half = size / 2.0
            lines = int(math.ceil(size / step))

            for i in range(-lines, lines+1):
                coord = i * step
                d = min(1.0, abs(coord) / fade_dist)
                c = 0.6 * (1.0 - d) + 0.15 * d
                self._grid.append(
                    ((c, c, c),
                     np.array([[self.center[0] - half, y, self.center[2] + coord],
                               [self.center[0] + half, y, self.center[2] + coord],
                               [self.center[0] + coord, y, self.center[2] - half],
                               [self.center[0] + coord, y, self.center[2] + half]], dtype=float)))

        glDisable(GL_LIGHTING)
        glLineWidth(1.0)
        glEnableClientState(GL_VERTEX_ARRAY)

        for color, arr in self._grid:
            glColor3f(*color)
            glVertexPointer(3, GL_DOUBLE, 0, arr)
            glDrawArrays(GL_LINES, 0, 4)

        glDisableClientState(GL_VERTEX_ARRAY)

        glEnable(GL_LIGHTING)

    def _on_erase_background(self, _):
        pass

    def _on_paint(self, _):
        _ = wx.PaintDC(self)
        self.SetCurrent(self.context)

        if not self.init:
            self.renderer.init()
            self.init = True

        with self.renderer:
            if self.update_objects:
                self.renderer.draw(self.editor3d.objects)
            else:
                self.renderer.draw()
                self.update_objects = True

            self.draw_grid(50, 50, 150)

        self.SwapBuffers()

    # override the _on_size method in the canvas
    def _on_size(self, event):
        wx.CallAfter(self._set_viewport)
        event.Skip()

    def world_coords(self, point: _point.Point) -> _point.Point:
        self.SetCurrent(self.context)

        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)

        factor_x, factor_y = self.GetContentScaleFactor()
        scale_factor = _point.Point(factor_x, factor_y)
        point *= scale_factor

        depth = glReadPixels(float(point.x), float(point.y), 1.0, 1.0, GL_DEPTH_COMPONENT, GL_FLOAT, None)
        x, y, z = gluUnProject(float(point.x), float(point.y), depth, modelview, projection, viewport)
        return _point.Point(x, y, z)

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
        e.SetArtist(self._selected_object)
        e.SetId(event.GetId())

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
        e.SetArtist(self._selected_object)
        e.SetId(event.GetId())

        self.GetParent().ProcessEvent(e)

        m_event._process()  # NOQA

    def _on_mouse_down(self, event: wx.MouseEvent):
        if self.HasCapture():
            self.ReleaseMouse()
        self.CaptureMouse()

        if event.LeftIsDown():
            self.last_left_x, self.last_left_y = event.GetPosition()
        elif event.RightIsDown():
            self.last_right_x, self.last_right_y = event.GetPosition()

    def _on_mouse_up(self, _):
        if self.HasCapture():
            self.ReleaseMouse()

    def _on_mouse_motion(self, event: wx.MouseEvent):
        if event.Dragging():
            x, y = event.GetPosition()

            if event.LeftIsDown():
                new_x = self.last_left_x - x
                new_y = self.last_left_y - y

                self.renderer.add_to_view_angle(new_x, new_y)
                self.last_left_x, self.last_left_y = x, y
                self.update_objects = False
                self.Refresh(False)

            elif event.RightIsDown():
                new_x = self.last_right_x - x
                new_y = self.last_right_y - y

                self.renderer.set_pan(new_x, new_y)
                self.last_right_x, self.last_right_y = x, y
                self.update_objects = False
                self.Refresh(False)

    def _on_mouse_wheel(self, event: wx.MouseEvent):
        scale = event.GetWheelRotation() / 20000
        scale = self.renderer.add_to_scale(scale, scale, scale)

        if scale < 0.001:
            scale = 0.001 - scale
            self.renderer.add_to_scale(scale, scale, scale)

        self.update_objects = False
        self.Refresh(False)
        event.Skip()

    def _set_viewport(self):
        self.SetCurrent(self.context)
        size = self.GetClientSize() * self.GetContentScaleFactor()
        glViewport(0, 0, size.width, size.height)

    def _on_enter(self, event):
        event.Skip()

    def _on_leave(self, event):
        event.Skip()

    def _on_capture_lost(self, event):
        if self.HasCapture():
            self.ReleaseMouse()

        event.Skip()
