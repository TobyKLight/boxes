# Copyright (C) 2013-2026 Florian Festi
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import math
import re

from boxes import *
from boxes import vectors


def argparsePoints(s):
    """Parse a list of XY coordinates: '0,0 120,0 100,80 20,70'"""
    if isinstance(s, (list, tuple)):
        return [(float(p[0]), float(p[1])) for p in s]

    s = s.strip()
    if not s:
        raise argparse.ArgumentTypeError("points must not be empty")

    points = []
    for token in re.split(r"\s+", s):
        if not token:
            continue
        for sep in (",", ";"):
            if sep in token:
                parts = token.split(sep)
                break
        else:
            raise argparse.ArgumentTypeError(
                f"point '{token}' must be x,y (e.g. 10,20)")
        if len(parts) != 2:
            raise argparse.ArgumentTypeError(
                f"point '{token}' must be x,y (e.g. 10,20)")
        try:
            points.append((float(parts[0]), float(parts[1])))
        except ValueError as e:
            raise argparse.ArgumentTypeError(
                f"point '{token}' must be numeric x,y") from e

    if len(points) >= 2 and math.dist(points[0], points[-1]) < 1e-6:
        points = points[:-1]

    if len(points) < 3:
        raise argparse.ArgumentTypeError(
            "points need at least 3 vertices to form a polygon")

    return points


class IrregularBox(Boxes):
    """Box with an irregular polygon as base"""

    description = """Provide consecutive polygon vertices as ``--points``
(space-separated ``x,y`` pairs in mm). The outline is closed automatically.

For short side walls that don't fit a connecting finger reduce
*surroundingspaces* and *finger* in the Finger Joint Settings.

The lids need to be glued.
"""

    ui_group = "Box"

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings, surroundingspaces=1)
        self.buildArgParser("h", "outside")
        self.argparser.add_argument(
            "--points", action="store", type=argparsePoints,
            default="0,0 120,0 100,80 20,70",
            help="polygon vertices as space-separated x,y pairs in mm")
        self.argparser.add_argument(
            "--top", action="store", type=str, default="none",
            choices=["none", "closed", "hole", "lid"],
            help="style of the top and lid")
        self.argparser.add_argument(
            "--bottom", action="store", type=str, default="closed",
            choices=["none", "closed", "hole", "lid"],
            help="style of the bottom and bottom lid")

    @staticmethod
    def _signedArea(points):
        area = 0.0
        n = len(points)
        for i in range(n):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % n]
            area += x1 * y2 - x2 * y1
        return area / 2.0

    @classmethod
    def _ensureCCW(cls, points):
        points = list(points)
        if cls._signedArea(points) < 0:
            points.reverse()
        return points

    @staticmethod
    def pointsToBorders(points):
        """Convert a closed XY ring to turtle borders (length, turn, ...)."""
        n = len(points)
        borders = []
        for i in range(n):
            p0 = points[i]
            p1 = points[(i + 1) % n]
            p2 = points[(i + 2) % n]
            length = math.dist(p0, p1)
            if length < 1e-9:
                raise ValueError("polygon has a zero-length edge")
            heading0 = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
            heading1 = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
            turn = (heading1 - heading0 + 180) % 360 - 180
            borders.append(length)
            borders.append(turn)
        return borders

    @staticmethod
    def _toLocalFrame(points):
        """Translate/rotate so first vertex is origin and first edge is +x."""
        p0 = points[0]
        p1 = points[1]
        angle = -math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        result = []
        for x, y in points:
            dx, dy = x - p0[0], y - p0[1]
            result.append((dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a))
        return result

    def holeCB(self):
        local = self._toLocalFrame(self.poly_points)
        inset = vectors.kerf(local, -self.thickness)
        # cc() places us at (0, burn) relative to the first outer vertex
        self.moveTo(0, -self.burn)
        x0, y0 = inset[0]
        x1, y1 = inset[1]
        heading = math.degrees(math.atan2(y1 - y0, x1 - x0))
        self.moveTo(x0, y0, heading)
        self.polygonWall(
            self.pointsToBorders(inset), edge="e",
            turtle=True, correct_corners=False)

    def _edgeFor(self, style):
        return "F" if style != "none" else "e"

    def _drawPanel(self, style, move="right"):
        if style == "none":
            return

        if style == "closed":
            self.polygonWall(self.borders, edge="f", move=move)
        elif style == "hole":
            self.polygonWall(
                self.borders, edge="f", callback=[self.holeCB], move=move)
        elif style == "lid":
            self.polygonWall(
                self.borders, edge="f", callback=[self.holeCB], move=move)
            self.polygonWall(self.lid_borders, edge="e", move=move)

    def render(self):
        points = self.points
        if isinstance(points, str):
            points = argparsePoints(points)

        points = self._ensureCCW(points)
        t = self.thickness

        if self.outside:
            points = vectors.kerf(points, -t)
            bottom_edge = self.bottom != "none"
            top_edge = self.top != "none"
            self.h = self.adjustSize(self.h, bottom_edge, top_edge)

        self.poly_points = points
        self.borders = self.pointsToBorders(points)
        self.lid_borders = self.pointsToBorders(
            vectors.kerf(points, t))

        with self.saved_context():
            self._drawPanel(self.bottom, move="right")
            self._drawPanel(self.top, move="right")

        self.polygonWall(self.borders, edge="f", move="up only")
        self.moveTo(0, t)

        self.polygonWalls(
            self.borders, self.h,
            bottom=self._edgeFor(self.bottom),
            top=self._edgeFor(self.top))
