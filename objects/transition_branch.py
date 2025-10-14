from mpl_toolkits.mplot3d import axes3d

from ...shapes import cylinder as _cylinder
from ...shapes import sphere as _sphere
from ...geometry import point as _point
from ...geometry import line as _line

from ...wrappers.decimal import Decimal as _decimal
from ...wrappers import color as _color

from . import bundle as _bundle
from . import handle as _handle


class TransitionBranch(_cylinder.Cylinder):

    def __init__(self, branch_id: str, origin: _point.Point, min_dia: _decimal,
                 max_dia: _decimal, wall: _decimal, length: _decimal,
                 angles: tuple[_decimal, _decimal, _decimal],
                 *bulb_data: list[dict]):

        self.branch_id = branch_id
        self._origin = origin
        self._diameter = min_dia
        self._min_dia = min_dia
        self._max_dia = max_dia
        self._wall = wall
        self._length = length
        self._bundle = None

        lgth = 0.0

        self._cylinders = []
        self._spheres = []

        self._primary_color = _color.Color(0, 0, 0, 255)
        self._edge_color = _color.Color(0, 0, 0, 255)

        for bulb in bulb_data:
            bulb_len = bulb['len'] - length
            bulb_dia = bulb['dia']

            if self._cylinders:
                bulb_origin = self._cylinders[-1].p2
            else:
                bulb_origin = origin

            line = _line.Line(bulb_origin, None, bulb_len, *angles)

            cylinder = _cylinder.Cylinder(bulb_origin.copy(), line.p2.copy(), bulb_dia, self._primary_color, self._edge_color)
            sphere = _sphere.Sphere(line.p2.copy(), bulb_dia, self._primary_color)
            self._cylinders.append(cylinder)
            self._spheres.append(sphere)
            length += bulb_len

        if self._cylinders:
            origin = self._cylinders[-1].p2.copy()

        line = _line.Line(origin, None, length - lgth, *angles)

        super().__init__(origin, line.p2.copy(), self.diameter, self._primary_color, self._edge_color)

    def set_x_angle(self, angle: _decimal, origin: _point.Point) -> None:
        with self:
            for cylinder in self._cylinders:
                cylinder.set_x_angle(angle, origin)

            for sphere in self._spheres:
                sphere.set_y_angle(angle, origin)

            super().set_x_angle(angle, origin)

            if self._bundle is not None:
                self._bundle.set_x_angle(angle, origin)

        self._update_artist()

    def set_y_angle(self, angle: _decimal, origin: _point.Point) -> None:
        with self:
            for cylinder in self._cylinders:
                cylinder.set_y_angle(angle, origin)

            for sphere in self._spheres:
                sphere.set_y_angle(angle, origin)

            super().set_y_angle(angle, origin)

            if self._bundle is not None:
                self._bundle.set_y_angle(angle, origin)

        self._update_artist()

    def set_z_angle(self, angle: _decimal, origin: _point.Point) -> None:
        with self:
            for cylinder in self._cylinders:
                cylinder.set_z_angle(angle, origin)

            for sphere in self._spheres:
                sphere.set_z_angle(angle, origin)

            super().set_z_angle(angle, origin)

            if self._bundle is not None:
                self._bundle.set_z_angle(angle, origin)

        self._update_artist()

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal,
                   origin: _point.Point) -> None:

        with self:
            for cylinder in self._cylinders:
                cylinder.set_angles(x_angle, y_angle, z_angle, origin)

            for sphere in self._spheres:
                sphere.set_angles(x_angle, y_angle, z_angle, origin)

            super().set_angles(x_angle, y_angle, z_angle, origin)

            if self._bundle is not None:
                self._bundle.set_angles(x_angle, y_angle, z_angle, origin)

        self._update_artist()

    def resize_to_fit_bundle(self, diameter: int | float) -> bool:
        if diameter < self._min_dia or diameter > self._max_dia:
            raise ValueError

        diameter += self._wall
        if diameter != self.diameter:
            self.diameter = diameter
            return True

        return False

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        for cylinder in self._cylinders:
            cylinder.add_to_plot(axes)

        for sphere in self._spheres:
            sphere.add_to_plot(axes)

        super().add_to_plot(axes)

    def hit_test(self, point: _point.Point, size: _decimal | None = None) -> bool:
        if self._bundle is not None:
            return False

        if size is None:
            size = self.diameter / _decimal(2.0)

        return (
            self._p2.x - size <= point.x <= self._p2.x + size and
            self._p2.y - size <= point.y <= self._p2.y + size and
            self._p2.z - size <= point.z <= self._p2.z + size
        )

    def move(self, point: _point.Point) -> None:
        for cylinder in self._cylinders:
            cylinder.move(point)

        for sphere in self._spheres:
            sphere.move(point)

        super().move(point)

    def add_bundle(self, bundle: _bundle.Bundle):
        diameter = bundle.diameter
        size = diameter / _decimal(2.0)

        if self.hit_test(bundle.p1, size):
            with self:
                self.resize_to_fit_bundle(diameter)
                bundle.handle1.remove()
                bundle.p1 = self._p2
        elif self.hit_test(bundle.p2, size):
            with self:
                self.resize_to_fit_bundle(diameter)
                bundle.handle2.remove()
                bundle.p2 = self._p2
        else:
            return None
