import matplotlib
import itertools
import matplotlib.cbook
import numpy as np
import io
from stl import mesh
from mpl_toolkits.mplot3d import axes3d, art3d

from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from ...wrappers import color as _color
from ...geometry import rotation as _rotation


class Model3D:

    def __init__(self, center: _point.Point, model_data: bytes, model_type: str, color: _color.Color):
        center.Bind(self._update_artist)
        self._center = center
        self._color = color
        self._saved_color = self._color
        self.artist = None
        self._verts = None
        self._model_data = io.BytesIO(model_data)
        self._model_type = model_type
        self._x_angle = _decimal(0.0)
        self._y_angle = _decimal(0.0)
        self._z_angle = _decimal(0.0)

    def set_selected_color(self, flag):
        if flag:
            self.color = _color.Color(153, 51, 51, 255)
        else:
            self.color = self._saved_color

    @property
    def color(self) -> _color.Color:
        return self._color

    @color.setter
    def color(self, value: _color.Color):
        self._color = value
        self._update_artist()

    @property
    def center(self) -> _point.Point:
        return self._center

    @center.setter
    def center(self, value: _point.Point):
        if not value.Bind(self._update_artist):
            if value != self._center:
                raise RuntimeError('sanity check')

            return

        self._center.Unbind(self._update_artist)
        self._center = value
        self._update_artist()

    @property
    def is_added(self) -> bool:
        return self.artist is not None

    def move(self, point: _point.Point) -> None:
        self._center += point

    def set_angles(self, x_angle: _decimal, y_angle: _decimal,
                   z_angle: _decimal, origin: _point.Point):

        if origin != self.center:
            self._center.set_angles(x_angle, y_angle, z_angle, origin)
            return

        self._x_angle = x_angle
        self._y_angle = y_angle
        self._z_angle = z_angle
        self._update_artist()

    def set_x_angle(self, angle: _decimal, origin: _point.Point) -> None:
        if origin != self._center:
            self.set_angles(angle, _decimal(0.0), _decimal(0.0), origin)
        else:
            self.set_angles(angle, self._y_angle, self._z_angle, origin)

    def set_y_angle(self, angle: _decimal, origin: _point.Point) -> None:
        if origin != self._center:
            self.set_angles(_decimal(0.0), angle, _decimal(0.0), origin)
        else:
            self.set_angles(self._x_angle, angle, self._z_angle, self._center)

    def set_z_angle(self, angle: _decimal, origin: _point.Point) -> None:
        if origin != self._center:
            self.set_angles(_decimal(0.0), _decimal(0.0), angle, origin)
        else:
            self.set_angles(self._x_angle, self._y_angle, angle, origin)

    def get_angles(self) -> tuple[_decimal, _decimal, _decimal]:
        return self._x_angle, self._y_angle, self._z_angle

    @property
    def _line_space(self):
        return np.pi / 2

    def _get_verts(self) -> tuple[np.array, np.array, np.array]:
        if self._verts is None:
            if self._model_type == 'stl':
                self._model_data.seek(0)
                stl = mesh.Mesh.from_file(self._model_data, calculate_normals=False)
                points = stl.points
                self._verts = [points[:, 0:: 3], points[:, 1:: 3], points[:, 2:: 3]]

            elif self._model_type == '3mf':
                self._model_data.seek(0)
                for mf in mesh.Mesh.from_3mf_file(self._model_data, calculate_normals=False):
                    points = mf.points
                    self._verts = [points[:, 0:: 3], points[:, 1:: 3], points[:, 2:: 3]]
                    break

        x, y, z = self._verts

        x_angle, y_angle, z_angle = self.get_angles()
        if x_angle or y_angle or z_angle:
            R = _rotation.Rotation(x_angle, y_angle, z_angle)

            X, Y, Z = R(self._center, x, y, z)
        else:
            X, Y, Z = x, y, z

        return X, Y, Z

    def _update_artist(self, p=None) -> None:
        if not self.is_added:
            return

        if p is not None:
            self._verts = None

        x, y, z = self._get_verts()

        z = matplotlib.cbook._to_unmasked_float_array(z)  # NOQA
        z, y, z = np.broadcast_arrays(x, y, z)
        rows, cols = z.shape

        has_stride = False
        has_count = False

        rstride = 10
        cstride = 10
        rcount = 50
        ccount = 50

        if matplotlib.rcParams['_internal.classic_mode']:
            compute_strides = has_count
        else:
            compute_strides = not has_stride

        if compute_strides:
            rstride = int(max(np.ceil(rows / rcount), 1))
            cstride = int(max(np.ceil(cols / ccount), 1))

        if (rows - 1) % rstride == 0 and (cols - 1) % cstride == 0:
            polys = np.stack([matplotlib.cbook._array_patch_perimeters(a, rstride, cstride)  # NOQA
                              for a in (x, y, z)], axis=-1)
        else:
            row_inds = list(range(0, rows - 1, rstride)) + [rows - 1]
            col_inds = list(range(0, cols - 1, cstride)) + [cols - 1]

            polys = []
            for rs, rs_next in itertools.pairwise(row_inds):
                for cs, cs_next in itertools.pairwise(col_inds):
                    ps = [matplotlib.cbook._array_perimeter(a[rs:rs_next + 1, cs:cs_next + 1])  # NOQA
                          for a in (x, y, z)]
                    ps = np.array(ps).T
                    polys.append(ps)

        if not isinstance(polys, np.ndarray) or not np.isfinite(polys).all():
            new_polys = []

            for p in polys:
                new_poly = np.array(p)[np.isfinite(p).all(axis=1)]

                if len(new_poly):
                    new_polys.append(new_poly)

            polys = new_polys

        self.artist.set_verts(polys)

        normals = art3d._generate_normals(polys)  # NOQA
        facecolors = art3d._shade_colors(self._color.matplotlib, normals, None)  # NOQA
        self.artist.set_facecolor(facecolors)

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        if self.is_added:
            return

        # we create an empty artist and then update the artist due to a bug in
        # matplotlib that causes the shading to not get rendered when updating
        # the color. We want the shading light source to be the same all the time.
        # To save some processor time we do the work of calculating the verts
        # only a single time.
        self.artist = axes.plot_surface(np.array([[np.NAN]], dtype=float),
                                        np.array([[np.NAN]], dtype=float),
                                        np.array([[np.NAN]], dtype=float),
                                        color=self._color, antialiaseds=False)
        self._update_artist()

    def set_py_data(self, py_data):
        if not self.is_added:
            raise ValueError('sanity check')

        self.artist.set_py_data(py_data)
