
from ...geometry import point as _point


_registered = {}
_active = None


def get_active_renderer_cls():
    return _active


def get_active_renderer():
    return _active.__name__


def get_renderers() -> list[str]:
    return list(_registered.keys())


def set_renderer_active(name: str):
    global _active
    if name not in _registered:
        raise NameError(name)

    _active = _registered[name]


class RendererMeta(type):

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        cls.__name__ = name
        _registered[name] = cls


class RendererBase(metaclass=RendererMeta):

    def __init__(self):
        self._up_down_angle = 0.0
        self._left_right_angle = 0.0
        self._near_far_angle = 0.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._pan_z = 0.0
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._scale_z = 1.0

    @classmethod
    def set_active(cls):
        global _active
        _active = cls

    def init(self, w: int | float, h: int | float):
        raise NotImplementedError

    def draw(self, *objs):
        raise NotImplementedError

    def look_at(self, *, camera_point: _point.Point | None = None,
                focus_point: _point.Point | None = None,
                direction_vector: _point.Point | None = None):
        pass

    def add_to_view_angle(self, x: float | None = None, y: float | None = None,
                          z: float | None = None) -> tuple[float, float, float]:
        if x is not None:
            self._left_right_angle += x
        if y is not None:
            self._up_down_angle += y
        if z is not None:
            self._near_far_angle += z

        return self._up_down_angle, self._left_right_angle, self._near_far_angle

    def set_view_angle(self, x: float | None = None, y: float | None = None,
                       z: float | None = None) -> None:
        if x is not None:
            self._left_right_angle = x
        if y is not None:
            self._up_down_angle = y
        if z is not None:
            self._near_far_angle = z

    def get_view_angle(self) -> tuple[float, float, float]:
        return self._up_down_angle, self._left_right_angle, self._near_far_angle

    def add_to_pan(self, x: float | None = None, y: float | None = None,
                   z: float | None = None) -> tuple[float, float, float]:
        if x is not None:
            self._pan_x += x
        if y is not None:
            self._pan_y += y
        if z is not None:
            self._pan_z += z

        return self._pan_x, self._pan_y, self._pan_z

    def set_pan(self, x: float | None = None, y: float | None = None,
                z: float | None = None) -> None:
        if x is not None:
            self._pan_x = x
        if y is not None:
            self._pan_y = y
        if z is not None:
            self._pan_z = z

    def get_pan(self) -> tuple[float, float, float]:
        return self._pan_x, self._pan_y, self._pan_z

    def add_to_scale(self, x: float | None = None, y: float | None = None,
                     z: float | None = None) -> tuple[float, float, float]:
        if x is not None:
            self._scale_x += x
        if y is not None:
            self._scale_y += y
        if z is not None:
            self._scale_z += z

        return self._scale_x, self._scale_y, self._scale_z

    def set_scale(self, x: float | None = None, y: float | None = None,
                  z: float | None = None) -> None:
        if x is not None:
            self._scale_x = x
        if y is not None:
            self._scale_y = y
        if z is not None:
            self._scale_z = z

    def get_scale(self) -> tuple[float, float, float]:
        return self._scale_x, self._scale_y, self._scale_z


