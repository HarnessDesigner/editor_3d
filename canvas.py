import wx
from matplotlib.backends.backend_wxagg import (  # NOQA
    FigureCanvasWxAgg as FigureCanvas
)


class Canvas(FigureCanvas):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)

    # bypass erasing the background when the plot is redrawn.
    # This helps to eliminate the flicker that is seen when a redraw occurs.
    # the second piece needed to eliminate the flicker is seen below
    def _on_erase_background(self, _):
        pass

    # override the _on_paint method in the canvas
    # this is done so double buffer is used which eliminates the flicker
    # that is seen when the plot redraws
    def _on_paint(self, event):
        drawDC = wx.BufferedPaintDC(self)
        if not self._isDrawn:
            self.draw(drawDC=drawDC)
        else:
            self.gui_repaint(drawDC=drawDC)
        drawDC.Destroy()

    # override the _on_size method in the canvas
    def _on_size(self, event):
        self._update_device_pixel_ratio()
        sz = self.GetParent().GetSizer()
        if sz:
            si = sz.GetItem(self)
        else:
            si = None

        if sz and si and not si.Proportion and not si.Flag & wx.EXPAND:
            size = self.GetMinSize()
        else:
            size = self.GetClientSize()
            size.IncTo(self.GetMinSize())

        if getattr(self, "_width", None):
            if size == (self._width, self._height):
                return

        self._width, self._height = size
        self._isDrawn = False

        if self._width <= 1 or self._height <= 1:
            return

        dpival = self.figure.dpi

        if wx.Platform != '__WXMSW__':
            scale = self.GetDPIScaleFactor()
            dpival /= scale

        winch = self._width / dpival
        hinch = self._height / dpival
        self.figure.set_size_inches(winch, hinch, forward=False)

        self.Refresh(eraseBackground=False)
        ResizeEvent("resize_event", self)._process()  # NOQA
        self.draw_idle()
