import numpy as np

import matplotlib
from mpl_toolkits.mplot3d import axes3d
from mpl_toolkits.mplot3d.axes3d import _Quaternion  # NOQA


# monkey patch the _on_move method for Axes3D
# this is done to change the handling of the right mouse button.
# the right mouse button pans the plot instead of zooming.
# The mouse wheel is used to zoom instead (as it should be)
def _on_move(self, event):
    if not self.button_pressed or event.key:
        return

    if self.get_navigate_mode() is not None:
        return

    if self.M is None:
        return

    x, y = event.xdata, event.ydata

    if x is None or event.inaxes != self:
        return

    dx, dy = x - self._sx, y - self._sy
    w = self._pseudo_w
    h = self._pseudo_h

    if self.button_pressed in self._rotate_btn:
        if dx == 0 and dy == 0:
            return

        style = matplotlib.rcParams['axes3d.mouserotationstyle']
        if style == 'azel':
            roll = np.deg2rad(self.roll)

            delev = (-(dy / h) * 180 * np.cos(roll) +
                     (dx / w) * 180 * np.sin(roll))

            dazim = (-(dy / h) * 180 * np.sin(roll) -
                     (dx / w) * 180 * np.cos(roll))

            elev = self.elev + delev
            azim = self.azim + dazim
            roll = self.roll
        else:
            q = _Quaternion.from_cardan_angles(
                *np.deg2rad((self.elev, self.azim, self.roll)))

            if style == 'trackball':
                k = np.array([0, -dy / h, dx / w])
                nk = np.linalg.norm(k)
                th = nk / matplotlib.rcParams['axes3d.trackballsize']
                dq = _Quaternion(np.cos(th), k * np.sin(th) / nk)
            else:  # 'sphere', 'arcball'
                current_vec = self._arcball(self._sx / w, self._sy / h)
                new_vec = self._arcball(x / w, y / h)
                if style == 'sphere':
                    dq = _Quaternion.rotate_from_to(current_vec, new_vec)
                else:  # 'arcball'
                    dq = (_Quaternion(0, new_vec) *
                          _Quaternion(0, -current_vec))

            q = dq * q
            elev, azim, roll = np.rad2deg(q.as_cardan_angles())

        vertical_axis = self._axis_names[self._vertical_axis]

        self.view_init(elev=elev, azim=azim, roll=roll,
                       vertical_axis=vertical_axis, share=True)

        self.stale = True

    elif self.button_pressed in self._zoom_btn:
        px, py = self.transData.transform([self._sx, self._sy])
        self.start_pan(px, py, 2)
        self.drag_pan(2, None, event.x, event.y)
        self.end_pan()

    self._sx, self._sy = x, y
    self.get_figure(root=True).canvas.draw_idle()


setattr(axes3d.Axes3D, '_on_move', _on_move)
