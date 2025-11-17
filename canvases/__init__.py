from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .. import Editor3D as _Editor3D

_registered = {}
_active = None


def get_active_canvas():
    return _active


class CanvasMeta(type):

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        _registered[name] = cls


class CanvasBase(metaclass=CanvasMeta):

    def __init__(self, editor3d: "_Editor3D"):
        self.editor3d = editor3d

    @classmethod
    def make_active(cls):
        global _active
        _active = cls

