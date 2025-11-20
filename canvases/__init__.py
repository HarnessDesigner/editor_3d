from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .. import Editor3D as _Editor3D

_registered = {}
_active = None


def get_active_canvas_cls():
    return _active


def get_active_canvas():
    return _active.__name__


def get_canvas() -> list[str]:
    return list(_registered.keys())


def set_canvas_active(name: str):
    global _active
    if name not in _registered:
        raise NameError(name)

    from .. import renderers

    if name == 'GLCanvas':
        if renderers.get_active_renderer() != 'GLRenderer':
            renderers.set_renderer_active('GLRenderer')
    elif renderers.get_active_renderer() == 'GLRenderer':
        raise RuntimeError('sanity check')

    _active = _registered[name]


class CanvasMeta(type):

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        _registered[name] = cls


class CanvasBase(metaclass=CanvasMeta):

    def __init__(self, editor3d: "_Editor3D", renderer):
        self.editor3d = editor3d
        self.renderer = renderer

    @classmethod
    def make_active(cls):
        global _active
        _active = cls

