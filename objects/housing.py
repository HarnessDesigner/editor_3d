from typing import TYPE_CHECKING


import build123d
import math
import tempfile
import os

from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from ...wrappers import color as _color
from ...geometry import angle as _angle
from . import Base3D as _Base3D


if TYPE_CHECKING:
    from .. import Editor3D as _Editor3D
    from ...database.global_db import housing as _housing
    from ...database.project_db import pjt_housing as _pjt_housing


def _read_step(data):
    temp_dir = tempfile.gettempdir()
    tmp_file_path = os.path.join(temp_dir, 'harness_designer_tmp.stp')
    with open(tmp_file_path, 'wb') as f:
        f.write(data)

    model = build123d.import_step(tmp_file_path)

    bb = model.bounding_box()
    corner1 = _point.Point(*[_decimal(float(item)) for item in bb.min])
    corner2 = _point.Point(*[_decimal(float(item)) for item in bb.max])

    try:
        os.remove(tmp_file_path)
    except OSError:
        pass

    return model, (corner1, corner2)


def _read_stl(data: bytes):
    temp_dir = tempfile.gettempdir()
    tmp_file_path = os.path.join(temp_dir, 'harness_designer_tmp.stl')
    with open(tmp_file_path, 'wb') as f:
        f.write(data)

    model = build123d.import_stl(tmp_file_path)

    bb = model.bounding_box()
    corner1 = _point.Point(*[_decimal(float(item)) for item in bb.min])
    corner2 = _point.Point(*[_decimal(float(item)) for item in bb.max])

    try:
        os.remove(tmp_file_path)
    except OSError:
        pass

    return model, (corner1, corner2)

def _build_model(h_data: "_housing.Housing"):
    length = h_data.length
    width = h_data.width
    height = h_data.height
    centerline = h_data.centerline
    num_pins = h_data.num_pins
    num_rows = h_data.rows
    gender = h_data.gender
    terminal_sizes = h_data.terminal_sizes

    if not length:
        if num_pins:
            if not centerline and terminal_sizes:
                centerline = terminal_sizes[0] * _decimal(1.20)

            if centerline and num_rows:
                pin_count = num_pins / num_rows
                length = pin_count * centerline + centerline
            elif centerline:
                length = num_pins * centerline + centerline

    if not width:
        if num_rows:
            width = _decimal(8) * num_rows
        else:
            width = _decimal(8)

    if not length:
        length = width * _decimal(2.0)

    if not height:
        height = width / length * width


    model = build123d.Box(float(length), float(width), float(height))
    box = build123d.Box(float(length), float(width * _decimal(0.90)), float(height * _decimal(0.90)))
    # z_axis = height
    # y_axis = width
    # x_axis = length
    box.move(build123d.Location((float(length / _decimal(3) / _decimal(2)), 0.0, 0.0)))
    model -= box

    if gender == 'Female':
        box = build123d.Box(float(length * _decimal(0.90)), float(width * _decimal(0.75)), float(height * _decimal(0.75)))
        box.move(build123d.Location((float((length - (length * _decimal(0.90))) / _decimal(2)), 0.0, 0.0)))
        model += box

    bb = model.bounding_box()
    corner1 = _point.Point(*[_decimal(float(item)) for item in bb.min])
    corner2 = _point.Point(*[_decimal(float(item)) for item in bb.max])

    return model, (corner1, corner2)


class Housing(_Base3D):

    _db_obj: "_pjt_housing.PJTHousing" = None

    def __init__(self, editor3d: "_Editor3D", housing_db: "_pjt_housing.PJTHousing"):
        super().__init__(editor3d)

        self.__update_disabled_count = 0
        self._part = housing_db.part

        self._color = self._part.color
        self._ui_color = self._color.ui
        self._ui_color.Bind(self.recalculate)

        self._center = housing_db.center.point
        self._center.Bind(self.recalculate)
        self._center.add_object(self)

        self._name = housing_db.name
        self._db_obj = housing_db

        model3d = self._part.model3d
        if model3d is not None:
            model_type = self._part.model3d_type
            if model_type == 'stl':
                self._model, self._hit_test_rect = _read_stl(model3d)
            elif model_type in ('stp', 'step'):
                self._model, self._hit_test_rect = _read_step(model3d)
            else:
                self._model = None
                self._hit_test_rect = None
        else:
            self._model = None
            self._hit_test_rect = None

        if self._model is None:
            self._model, self._hit_test_rect = _build_model(self._part)

        self._triangles = None
        self._normals = None
        self._triangle_count = 0

        p1, p2 = self._hit_test_rect

        self._angle = housing_db.angle_3d
        p1 @= self._angle
        p1 += self._center

        p2 @= self._angle
        p2 += self._center

    def recalculate(self, *_):
        self._triangles = None

    def hit_test(self, point: _point.Point) -> bool:
        p1, p2 = self._hit_test_rect
        return p1 <= point <= p2

    def draw(self, renderer):
        if self._triangles is None:
            self._normals, self._triangles, self._triangle_count = self._get_triangles(self._model)

            self._triangles @= self._angle
            self._triangles += self._center.as_numpy

        renderer.draw_triangles(self._normals, self._triangles, self._triangle_count, self._ui_color.rgb_scalar)

    @property
    def color(self) -> _color.Color:
        return self._ui_color

    @property
    def angle(self) -> _angle.Angle:
        return self._angle

    @angle.setter
    def angle(self, value: _angle.Angle):
        angle_diff = value - self._angle

        self._angle += angle_diff

        p1, p2 = self._hit_test_rect
        p1 -= self._center
        p1 @= angle_diff
        p1 += self._center

        p2 -= self._center
        p2 @= angle_diff
        p2 += self._center

        if self._triangles is not None:
            self._triangles -= self._center.as_numpy
            self._triangles @= angle_diff
            self._triangles += self._center.as_numpy

    def move(self, point: _point.Point) -> None:
        p1, p2 = self._hit_test_rect
        p1 += point
        p2 += point
        self._center += point
