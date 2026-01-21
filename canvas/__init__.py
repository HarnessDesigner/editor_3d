from typing import TYPE_CHECKING
import wx

from . import canvas as _canvas

from harness_designer import Config

try:
    from ..geometry import point as _point
    from ..wrappers.wrap_decimal import Decimal as _decimal
    from .. import axis_indicators as _axis_indicators
except ImportError:
    from geometry import point as _point  # NOQA
    from wrappers.wrap_decimal import Decimal as _decimal  # NOQA
    import axis_indicators as _axis_indicators  # NOQA


if TYPE_CHECKING:
    from .. import Editor3D as _Editor3D


