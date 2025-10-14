
from ...wrappers.decimal import Decimal as _decimal
from ...geometry import point as _point

from ...shapes import box as _box


class Terminal(_box.Box):

    def __init__(self, blade_width: _decimal.Decimal, gender: int):
        point = _point.Point(0, 0, 0)


