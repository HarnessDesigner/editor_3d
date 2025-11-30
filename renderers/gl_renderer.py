from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import numpy as np

from . import RendererBase
from ...geometry import point as _point
from ... import gl_materials as _gl_materials


class GLRenderer(RendererBase):

    def __init__(self):
        super().__init__()
        self.viewMatrix = None
        self._total_pan = [0.0, 0.0, 0.0]

    def look_at(self, *, camera_point: _point.Point | None = None,
                focus_point: _point.Point | None = None,
                direction_vector: _point.Point | None = None):
        """
        cam_x, cam_y, cam_z = camera_point.as_float
        foc_x, foc_y, foc_z = focus_point.as_float
        up_x, up_y, up_z = direction_vector.as_float

        F = np.array([foc_x - cam_x, foc_y - cam_y, foc_z - cam_z], dtype=np.dtypes.Float64DType)
        f = F / F

        UP = np.array([up_x, up_y, up_z], dtype=np.dtypes.Float64DType)
        up = UP / UP
        s = f * up
        u = s / s * f

        M = np.array([[s[0], s[1], s[2], 0.0],
                      [u[0], u[1], u[2], 0.0]
                      [-f[0], -f[1], -f[2], 0.0]
                      [0.0, 0.0, 0.0, 1.0]])
        """
        args = camera_point.as_float + focus_point.as_float + direction_vector.as_float
        gluLookAt(*args)

    def init(self, w: int | float, h: int | float):
        glClearColor(0.95, 0.95, 0.95, 0.0)
        glViewport(0, 0, w, h)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_COLOR_MATERIAL)
        # glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.1, 0.1, 0.1, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.1, 0.1, 0.1, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])

        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, w / float(h), 0.1, 1000.0)

        glMatrixMode(GL_MODELVIEW)
        gluLookAt(0.0, 2.0, -100.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        self.viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)

    def set_pan(self, x: float | None = None, y: float | None = None,
                z: float | None = None) -> None:
        if x is not None:
            self._pan_x = x
            self._total_pan[0] += x
        if y is not None:
            self._pan_y = y
            self._total_pan[1] += y
        if z is not None:
            self._pan_z = z
            self._total_pan[2] += z

    def get_pan(self) -> tuple[float, float, float]:
        return tuple(self._total_pan)

    def draw(self, *objs):
        if objs:
            # Clear color and depth buffers.
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            glPushMatrix()

            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_NORMAL_ARRAY)

            for obj in objs:
                obj.draw(self)

            glDisableClientState(GL_VERTEX_ARRAY)
            glDisableClientState(GL_NORMAL_ARRAY)
            glPopMatrix()

    @staticmethod
    def draw_trinagles(normals: np.ndarray | None, triangles: np.ndarray | None,
                       triangle_count: int, color: tuple[float, float, float, float],
                       material: _gl_materials.GLMaterial | None):

        if triangle_count != 0:
            glColor4f(*color)
            if material is not None:
                material.set()

            glVertexPointer(3, GL_DOUBLE, 0, triangles)
            glNormalPointer(GL_DOUBLE, 0, normals)
            glDrawArrays(GL_TRIANGLES, 0, triangle_count)

    def __enter__(self):
        glLoadIdentity()
        glRotatef(self._up_down_angle * 0.1, 1.0, 0.0, 0.0)
        glRotatef(self._left_right_angle * 0.1, 0.0, 1.0, 0.0)

        glPushMatrix()
        glLoadIdentity()

        if self._pan_x:
            glTranslatef(-self._pan_x * 0.1, 0, 0)
            self._pan_x = 0.0

        if self._pan_y:
            glTranslatef(0, self._pan_y * 0.1, 0)
            self._pan_y = 0.0

        glMultMatrixf(self.viewMatrix)
        self.viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)

        glPopMatrix()
        glMultMatrixf(self.viewMatrix)

        glScalef(self._scale_x, self._scale_y, self._scale_z)
        return self


GLRenderer.set_active()
