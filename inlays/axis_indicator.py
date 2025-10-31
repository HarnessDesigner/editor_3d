import numpy as np
from mpl_toolkits.mplot3d import axes3d


class AxisIndicator(axes3d.Axes3D):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.grid(False)
        self.patch.set_visible(False)
        self.set_axis_off()

        self.plot_surface(*self.plot_cone((-13, 13, 7), 0.0, 0.0,
                                          0.0, 4.0, 3.0),
                          color=(1.0, 0.0, 0.0, 1.0), alpha=1.0, linewidth=0)

        self.plot_surface(*self.plot_cylinder((-13, 13, -13), 0.0, 0.0,
                                              0.0, 20, 1.0),
                          color=(1.0, 0.0, 0.0, 1.0), alpha=1.0, linewidth=0)

        self.plot_surface(*self.plot_cone((-13, -7, -13), -90.0, 0.0,
                                          0.0, 4.0, 3.0),
                          color=(0.0, 1.0, 0.0, 1.0), alpha=1.0, linewidth=0)

        self.plot_surface(*self.plot_cylinder((-13, 13, -13), -90.0, 0.0,
                                              0.0, 20,  1.0),
                          color=(0.0, 1.0, 0.0, 1.0), alpha=1.0, linewidth=0)

        self.plot_surface(*self.plot_cone((7, 13, -13), 0.0, -90.0,
                                          0.0, 4.0, 3.0),
                          color=(0.0, 0.0, 1.0, 1.0), alpha=1.0, linewidth=0)

        self.plot_surface(*self.plot_cylinder((-13, 13, -13), 0.0, -90.0,
                                              0.0, 20, 1.0),
                          color=(0.0, 0.0, 1.0, 1.0), alpha=1.0, linewidth=0)

        x_label = self.text(-14, 14, 14, "Z", color=(1.0, 0.0, 0.0, 1.0))
        y_label = self.text(-14, -14, -14, "Y", color=(0.0, 1.0, 0.0, 1.0))
        z_label = self.text(14, 14, -14, "X", color=(0.0, 0.0, 1.0, 1.0))

        x_label.set_fontsize(12.0)
        y_label.set_fontsize(12.0)
        z_label.set_fontsize(12.0)

        self.set_xlim3d(-13, 13)
        self.set_ylim3d(-13, 13)
        self.set_zlim3d(-13, 13)

    def plot_cone(self, center, x_angle, y_angle, z_angle,
                  height, diameter, flare=1.0):

        Ra = self._rotation_matrix(x_angle, y_angle, z_angle)

        radius = diameter / 2.0

        cx, cy, cz = center

        theta = np.linspace(0, 2 * np.pi, 25)
        z = np.linspace(0, height, 25)
        Theta, Z = np.meshgrid(theta, z)

        flare = max(0.1, flare)
        R = radius * (1 - (Z / height) ** flare)
        X = R * np.cos(Theta)
        Y = R * np.sin(Theta)

        pts = np.stack((X, Y, Z), axis=-1).reshape(-1, 3)
        pts_rot = pts @ Ra
        Xr = pts_rot[:, 0].reshape(X.shape) + cx
        Yr = pts_rot[:, 1].reshape(Y.shape) + cy
        Zr = pts_rot[:, 2].reshape(Z.shape) + cz

        return Xr, Yr, Zr

    def plot_cylinder(self, p1, x_angle, y_angle, z_angle, length, diameter):
        A2B = np.eye(4)
        x, y, z = p1

        R = self._rotation_matrix(x_angle, y_angle, z_angle)

        t = np.array([0, length])
        angles = np.linspace(0, 2 * np.pi, length)
        t, angles = np.meshgrid(t, angles)

        A2B = np.asarray(A2B)
        axis_start = np.dot(A2B, [0, 0, 0, 1])[:3]
        X, Y, Z = self._elongated_circular_grid(axis_start, A2B, t,
                                                diameter / 2.0, angles)

        pts = np.stack((X, Y, Z), axis=-1).reshape(-1, 3)
        pts_rot = pts @ R
        X = pts_rot[:, 0].reshape(X.shape) + x
        Y = pts_rot[:, 1].reshape(Y.shape) + y
        Z = pts_rot[:, 2].reshape(Z.shape) + z

        return X, Y, Z

    @staticmethod
    def _elongated_circular_grid(bottom_point, A2B, height_fractions, radii, angles):
        return [bottom_point[i] + radii * np.sin(angles) * A2B[i, 0] +
                radii * np.cos(angles) * A2B[i, 1] + A2B[i, 2] * height_fractions
                for i in range(3)]

    @staticmethod
    def _rotation_matrix(angle_x, angle_y, angle_z):
        x_angle = np.radians(float(angle_x))
        y_angle = np.radians(float(angle_y))
        z_angle = np.radians(float(angle_z))

        Rx = np.array([[1, 0, 0],
                       [0, np.cos(x_angle), -np.sin(x_angle)],
                       [0, np.sin(x_angle), np.cos(x_angle)]])

        Ry = np.array([[np.cos(y_angle), 0, np.sin(y_angle)],
                       [0, 1, 0],
                       [-np.sin(y_angle), 0, np.cos(y_angle)]])

        Rz = np.array([[np.cos(z_angle), -np.sin(z_angle), 0],
                       [np.sin(z_angle), np.cos(z_angle), 0],
                       [0, 0, 1]])

        return Rz @ Ry @ Rx
