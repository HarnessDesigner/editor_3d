

from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from ...wrappers import color as _color
from ...shapes import sphere as _sphere


class WireHandle(_sphere.Sphere):

    def __init__(self, point: _point.Point, diameter: _decimal, color: _color.Color):
        super().__init__(point, diameter, color)

        self._wires = []

    def remove(self):
        self._center.UnBind(self._update_artist)
        if self.is_added:
            self.artist.remove()
            self.artist = None

    def add_wire(self, wire: "_wire.Wire"):
        if wire not in self._wires:
            self._wires.append(wire)

    def remove_wire(self, wire: "_wire.Wire"):
        if wire in self._wires:
            self._wires.remove(wire)


class BundleHandle(_sphere.Sphere):

    def __init__(self, point: _point.Point, diameter: _decimal):

        color = _color.Color(0, 0, 0, 255)
        color = color.GetLighterColor(25)

        super().__init__(point, diameter, color)

        self._bundles = []

    def remove(self):
        self._center.UnBind(self._update_artist)
        if self.is_added:
            self.artist.remove()
            self.artist = None

    def add_bundle(self, bundle: "_bundle.Bundle"):
        if bundle not in self._bundles:
            self._bundles.append(bundle)

    def remove_bundle(self, bundle: "_bundle.Bundle"):
        if bundle in self._bundles:
            self._bundles.remove(bundle)


from . import wire as _wire  # NOQA
from . import bundle as _bundle  # NOQA
