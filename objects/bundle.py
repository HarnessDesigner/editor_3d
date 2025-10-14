from mpl_toolkits.mplot3d import axes3d

from ...shapes import cylinder as _cylinder
from ...geometry import point as _point

from ...wrappers.decimal import Decimal as _decimal
from ...wrappers import color as _color


from . import handle as _handle
from . import layout as _layout
from . import wire as _wire


class Bundle(_cylinder.Cylinder):

    def __init__(self, p1: _point.Point, p2: _point.Point, diameter: _decimal, color: _color.Color):

        self._handle1 = _handle.BundleHandle(p1, diameter)
        self._handle2 = _handle.BundleHandle(p2, diameter)

        super().__init__(p1, p2, diameter, color, color)

        self._handle1.add_bundle(self)
        self._handle2.add_bundle(self)
        self._wires = []

    @property
    def p1(self) -> _point.Point:
        return self._p1

    @p1.setter
    def p1(self, value: _point.Point):
        self._p1.UnBind(self._update_artist)
        self._p1 = value

        self._handle1.center = value
        self._update_artist()

    @property
    def p2(self) -> _point.Point:
        return self._p2

    @p2.setter
    def p2(self, value: _point.Point):
        self._p2.UnBind(self._update_artist)
        self._p2 = value

        self._handle2.center = value
        self._update_artist()

    @property
    def handle1(self) -> _handle.BundleHandle | _layout.BundleLayout:
        return self._handle1

    @handle1.setter
    def handle1(self, value: _handle.BundleHandle | _layout.BundleLayout):
        self._handle1.remove_bundle(self)
        self._p1.UnBind(self._update_artist)
        value.center.Bind(self._update_artist)
        self._p1 = value.center
        self._p1.Bind(self._update_artist)
        self._handle1 = value

    @property
    def handle2(self) -> _handle.BundleHandle | _layout.BundleLayout:
        return self._handle2

    @handle2.setter
    def handle2(self, value: _handle.BundleHandle | _layout.BundleLayout):
        self._handle2.remove_bundle(self)
        self._p2.UnBind(self._update_artist)
        value.center.Bind(self._update_artist)
        self._p2 = value.center
        self._p2.Bind(self._update_artist)
        self._handle2 = value

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        super().add_to_plot(axes)

        if self._handle1 is not None:
            self._handle1.add_to_plot(axes)
        if self._handle2 is not None:
            self._handle2.add_to_plot(axes)

    def add_wire(self, wire: _wire.Wire):

        if wire not in self._wires:
            self._wires.append(wire)
            wire.hide()

    def remove_wire(self, wire: _wire.Wire):
        if wire in self._wires:
            self._wires.remove(wire)
            wire.show()

    @property
    def wires(self):
        return self._wires[:]

    def add_layout(self, point: _point.Point) -> "Bundle":
        p2 = self._p2
        p2.UnBind(self._update_artist)

        point.Bind(self._update_artist)
        self._p2 = point

        layout = _layout.BundleLayout(point, self._diameter)
        layout.add_bundle(self)

        bundle = Bundle(point, p2, self.diameter, self._primary_color)

        layout.add_bundle(bundle)

        bundle.handle1.remove()
        bundle.handle1 = layout

        self._handle2.remove()
        self._handle2 = layout

        return bundle
