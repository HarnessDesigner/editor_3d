from mpl_toolkits.mplot3d import axes3d
import numpy as np

from ...geometry import point as _point
from ...wrappers import color as _color
from ...wrappers.decimal import Decimal as _decimal

from ...shapes import box as _box
from ...shapes import cad as _cad


class Connector:

    def __init__(self, point: _point.Point, length: _decimal, width: _decimal,
                 height: _decimal, color: _color.Color, shade: bool, filename: str | None,
                 pitch: _decimal, *wire_coords):

        edge_color = color.GetDarkerColor()

        if filename is None:
            self._shape = _box.Box(point, length, width, height, color, edge_color)
        else:
            self._shape = _cad.CAD(point, length, width, height, color, shade, filename)

        self._pitch = pitch

        self._wire_coords = list(wire_coords)

        if wire_coords:
            self._wires = {coord: [] for coord in wire_coords}
        else:
            self._wires = {self.center: []}

    def move(self, point: _point.Point) -> None:
        self._shape.move(point)
        for p in self._wire_coords:
            p += point

    def _set_angles(self):
        x_angle, y_angle, z_angle = self._shape.get_angles()
        x_angle = np.radians(float(x_angle))
        y_angle = np.radians(float(y_angle))
        z_angle = np.radians(float(z_angle))

        Rx = np.array(
            [[1, 0, 0],
             [0, np.cos(x_angle), -np.sin(x_angle)],
             [0, np.sin(x_angle), np.cos(x_angle)]]
        )

        Ry = np.array(
            [[np.cos(y_angle), 0, np.sin(y_angle)],
             [0, 1, 0],
             [-np.sin(y_angle), 0, np.cos(y_angle)]]
        )

        Rz = np.array(
            [[np.cos(z_angle), -np.sin(z_angle), 0],
             [np.sin(z_angle), np.cos(z_angle), 0],
             [0, 0, 1]]
        )

        R = Rz @ Ry @ Rx

        xyz = np.array(self.center.as_float, dtype=float)

        for point in self._wire_coords:
            p = np.array(point.as_float, dtype=float)
            p = ((p - xyz) @ R) + xyz

            with point:
                point.x = _decimal(float(p[0]))
                point.y = _decimal(float(p[1]))
                point.z = _decimal(float(p[2]))

    def get_angles(self) -> tuple[_decimal, _decimal, _decimal]:
        return self._shape.get_angles()

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, _) -> None:
        self._shape.set_angles(x_angle, y_angle, z_angle, None)
        self._set_angles()

    def get_x_angle(self) -> _decimal:
        return self._shape.get_x_angle()

    def get_y_angle(self) -> _decimal:
        return self._shape.get_x_angle()

    def get_z_angle(self) -> _decimal:
        return self._shape.get_x_angle()

    def set_x_angle(self, angle: _decimal, _):
        self._shape.set_x_angle(angle, None)
        self._set_angles()

    def set_y_angle(self, angle: _decimal, _):
        self._shape.set_y_angle(angle, None)
        self._set_angles()

    def set_z_angle(self, angle: _decimal, _):
        self._shape.set_z_angle(angle, None)
        self._set_angles()

    @property
    def center(self) -> _point.Point:
        return self._shape.center

    @center.setter
    def center(self, value: _point.Point):
        self._shape.center = value

    @property
    def color(self) -> _color.Color:
        return self._shape.center

    @color.setter
    def color(self, value: _color.Color):
        self._shape.color = value

    @property
    def length(self) -> _decimal:
        return self._shape.length

    @length.setter
    def length(self, value: _decimal):
        self._shape.length = value

    @property
    def width(self) -> _decimal:
        return self._shape.width

    @width.setter
    def width(self, value: _decimal):
        self._shape.width = value

    @property
    def height(self) -> _decimal:
        return self._shape.height

    @height.setter
    def height(self, value: _decimal):
        self._shape.height = value

    def add_to_plot(self, axes: axes3d.Axes3D):
        self._shape.add_to_plot(axes)

    def _update_artist(self):
        self._shape._update_artist()  # NOQA

    def hit_test(self, point: _point.Point):
        return self._shape.hit_test(point)

    def get_wire_attach(self, point: _point.Point) -> _point.Point:
        if self._wire_coords:
            pitch = self._pitch / _decimal(2.0)

            for wire_point in self._wires.keys():
                x1 = wire_point.x - pitch
                x2 = wire_point.x + pitch

                y1 = wire_point.y - pitch
                y2 = wire_point.y + pitch

                z1 = wire_point.z - pitch
                z2 = wire_point.z + pitch

                if x1 <= point.x <= x2 and y1 <= point.y <= y2 and z1 <= point.z <= z2:
                    return wire_point
        else:
            return self.center

        return None

    def add_wire(self, wire):
        if self.hit_test(wire.p1):
            p = self.get_wire_attach(wire.p1)

            if p is None:
                return False

            wire.handle1.remove()
            wire.handle1 = None
            wire.p1 = p
            self._wires[p].append(wire)

        elif self.hit_test(wire.p2):
            p = self.get_wire_attach(wire.p2)

            if p is None:
                return False

            wire.handle2.remove()
            wire.handle2 = None
            wire.p2 = p
            self._wires[p].append(wire)
        else:
            raise ValueError

