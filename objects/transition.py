from mpl_toolkits.mplot3d import axes3d


from .transition_branch import TransitionBranch
from ... import bases
from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal


class Transition(bases.GetAngleBase, bases.SetAngleBase):

    def __init__(self, part_number: str, point: _point.Point):
        self.part_number = part_number
        self._point = point
        self._x_angle = 0
        self._y_angle = 0
        self._z_angle = 0
        self._branches = []

    def AddBranch(self, branch_id: str, origin: _point.Point, min_dia: _decimal,
                  max_dia: _decimal, wall: _decimal, length: _decimal,
                  angles: tuple[_decimal, _decimal, _decimal], *bulbs):

        origin += self._point.copy()

        branch = TransitionBranch(branch_id, origin, min_dia, max_dia,
                                  wall, length, angles,
                                  *bulbs)
        self._branches.append(branch)

    def hit_test(self, point: _point.Point) -> bool:
        for branch in self._branches:
            if branch.hit_test(point):
                return True

        return False

    def get_selected_branch(self, point: _point.Point) -> TransitionBranch:
        for branch in self._branches:
            if branch.hit_test(point):
                return branch

        raise ValueError

    def add_to_plot(self, axes: axes3d.Axes3D) -> None:
        for branch in self._branches:
            branch.add_to_plot(axes)

    def get_x_angle(self) -> _decimal:
        return self._x_angle

    def set_x_angle(self, angle: _decimal, _) -> None:
        for branch in self._branches:
            branch.set_x_angle(angle, self._point)

        self._x_angle = angle

    def get_y_angle(self) -> _decimal:
        return self._y_angle

    def set_y_angle(self, angle: _decimal, _) -> None:
        for branch in self._branches:
            branch.set_y_angle(angle, self._point)

        self._y_angle = angle

    def get_z_angle(self) -> _decimal:
        return self._z_angle

    def set_z_angle(self, angle: _decimal, _) -> None:
        for branch in self._branches:
            branch.set_z_angle(angle, self._point)

        self._z_angle = angle

    def set_angles(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal, _):
        for branch in self._branches:
            branch.set_angles(x_angle, y_angle, z_angle, self._point)

        self._x_angle = x_angle
        self._y_angle = y_angle
        self._z_angle = z_angle

    def move(self, point: _point.Point) -> None:
        self._point += point

        for branch in self._branches:
            branch.move(point)
