

from . import handle as _handle


class WireLayout(_handle.WireHandle):

    def remove(self):
        wire1, wire2 = self._wires
        wire1.p1.UnBind(self._update_artist)
        wire1.handle2 = wire2.handle2

        wire2.handle1.remove()
        wire2.remove()
        self.artist.remove()
        self.artist = None


class BundleLayout(_handle.BundleHandle):

    def remove(self):
        bundle1, bundle2 = self._bundles
        bundle1.p1.UnBind(self._update_artist)
        bundle1.handle2 = bundle2.handle2

        bundle2.handle1.remove()
        bundle2.remove()
        self.artist.remove()
        self.artist = None

