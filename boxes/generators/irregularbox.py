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
import copy
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

Use *join* to choose finger joints or T-slots between panels and walls.
With T-slots, *tslot_on* selects which side carries the T-cutouts.
Side walls are inset by *inner_offset* (default one material thickness) so they
sit within the top/bottom panels and the T-slots are closed by the panel.
*wall_joints* controls vertical wall-to-wall edges (finger joints or plain).

For short side walls that don't fit a connecting finger reduce
*surroundingspaces* and *finger* in the Finger Joint Settings.
For short edges with T-slots enable *allow_cropped* in the T-Slot Settings.

The lids need to be glued.
"""

    ui_group = "Box"

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings, surroundingspaces=1)
        self.addSettingsArgs(edges.TSlotSettings)
        self.buildArgParser("h", "outside")
        self.argparser.add_argument(
            "--points", action="store", type=argparsePoints,
            default="0,0 120,0 100,80 20,70",
            help="polygon vertices as space-separated x,y pairs in mm")
        self.argparser.add_argument(
            "--top", action="store", type=str, default="closed",
            choices=["none", "closed", "hole", "lid"],
            help="style of the top and lid")
        self.argparser.add_argument(
            "--bottom", action="store", type=str, default="closed",
            choices=["none", "closed", "hole", "lid"],
            help="style of the bottom and bottom lid")
        self.argparser.add_argument(
            "--join", action="store", type=str, default="tslot",
            choices=["finger", "tslot"],
            help="join style between panels and walls")
        self.argparser.add_argument(
            "--tslot_on", action="store", type=str, default="panels",
            choices=["walls", "panels"],
            help="which side gets T-slots when join is tslot")
        self.argparser.add_argument(
            "--wall_joints", action="store", type=str, default="finger",
            choices=["finger", "none"],
            help="vertical wall-to-wall joints")

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

    def _panelEdge(self):
        """Edge char / objects used on top/bottom panels for panel↔wall joins."""
        if self.join == "tslot":
            if self.tslot_on == "walls":
                # Plain outline; mate holes via callback aligned to inset walls.
                return "e"
            # One centered T-slot edge object per polygon side.
            n = len(self.borders) // 2
            return [self._CenteredPanelTSlot(self, i) for i in range(n)]
        return "f"

    class _CenteredPanelTSlot:
        """T-slot pattern sized to the inset wall, centered on one panel edge."""

        def __init__(self, box, index):
            self.box = box
            self.index = index
            self.settings = box.edges["w"].settings

        def margin(self):
            return self.box.edges["w"].margin()

        def startWidth(self):
            return self.box.edges["w"].startWidth()

        def endWidth(self):
            return self.startWidth()

        def spacing(self):
            return self.startWidth() + self.margin()

        def __call__(self, length, **kw):
            wall_len = self.box.wall_borders[2 * self.index]
            lo = (length - wall_len) / 2.0
            if lo > 1e-9:
                self.box.edge(lo)
            self.box.edges["w"].drawPattern(wall_len)
            if lo > 1e-9:
                self.box.edge(lo)

    def _wallTBEdge(self, style):
        """Top/bottom edge char on walls for a given panel style."""
        if style == "none":
            return "e"
        if self.join == "tslot":
            return "w" if self.tslot_on == "walls" else "e"
        return "F"

    def _tslotMateHoles(self, number, path_borders, slot_borders, on_outer_panel=True):
        """Draw tab slots + bolt holes for edge ``number``, aligned to slots."""
        settings = self.edges["w"].settings
        slot_len = slot_borders[2 * number]
        path_len = path_borders[2 * number]
        n, centers, layout = settings.calcSlots(slot_len)
        if not n or layout is None:
            return

        play = settings.play
        t = self.thickness
        inset = settings.inner_offset
        tab_offset = layout["tab_offset"]
        tab_width = layout["tab_width"] + play
        bolt_r = 0.5 * (settings.bolt + play)
        # Center the (possibly shorter) slot pattern on this edge.
        shift = (path_len - slot_len) / 2.0
        # Always keep an inner_offset lip from the joining edge, then center
        # holes on the mating material thickness (panel on wall, or wall on
        # outer panel).
        y = self.burn + inset + t / 2.0
        for cx in centers:
            x = shift + cx
            self.rectangularHole(x - tab_offset, y, tab_width, t + play)
            self.rectangularHole(x + tab_offset, y, tab_width, t + play)
            self.hole(x, y, bolt_r)

    def _panelMateCB(self, number):
        # Panels are the outer path; slots come from inset walls.
        self._tslotMateHoles(
            number, self.borders, self.wall_borders, on_outer_panel=True)

    def _panelHoleAndMateCB(self, number):
        if number == 0:
            self.holeCB()
        self._panelMateCB(number)

    def _drawPanel(self, style, move="right"):
        if style == "none":
            return

        edge = self._panelEdge()
        mate = self.join == "tslot" and self.tslot_on == "walls"

        if style == "closed":
            cb = self._panelMateCB if mate else None
            self.polygonWall(self.borders, edge=edge, callback=cb, move=move)
        elif style == "hole":
            cb = self._panelHoleAndMateCB if mate else [self.holeCB]
            self.polygonWall(self.borders, edge=edge, callback=cb, move=move)
        elif style == "lid":
            cb = self._panelHoleAndMateCB if mate else [self.holeCB]
            self.polygonWall(self.borders, edge=edge, callback=cb, move=move)
            self.polygonWall(self.lid_borders, edge="e", move=move)

    def _polygonWallsStraight(self, borders, h, bottom, top):
        """Walls with plain vertical edges (butt joints)."""
        borders = self._closePolygon(borders)
        bottom_e = self.edges.get(bottom, bottom)
        top_e = self.edges.get(top, top)
        i = 0
        while i < len(borders):
            length = borders[i]
            self.rectangularWall(
                length, h, [bottom_e, "e", top_e, "e"], move="right")
            i += 2

    def _mateEdge(self, idx):
        """Plain edge that also draws T-slot counterpart holes for wall edge idx."""
        box = self

        class _Mate:
            def margin(self):
                return 0.0

            def startWidth(self):
                return 0.0

            def endWidth(self):
                return 0.0

            def spacing(self):
                return 0.0

            def __call__(self, length, **kw):
                box._tslotMateHoles(
                    idx, box.wall_borders, box.wall_borders,
                    on_outer_panel=False)
                box.edge(length, tabs=2)

        return _Mate()

    def _polygonWallsTSlotMate(self, wall_borders, h, mate_bottom, mate_top):
        """Walls with T-slot counterpart holes (tslot_on=panels).

        Vertical edges follow ``wall_joints`` (finger or none), matching
        ``polygonWalls`` pairing/angles when fingers are enabled.
        """
        wall_borders = self._closePolygon(wall_borders)
        use_fingers = self.wall_joints == "finger"

        if use_fingers:
            leftsettings = copy.deepcopy(self.edges["f"].settings)
            lf, lF, _lh = leftsettings.edgeObjects(self, add=False)
            rightsettings = copy.deepcopy(self.edges["f"].settings)
            rf, rF, _rh = rightsettings.edgeObjects(self, add=False)

        length_correction = 0.0
        angle = wall_borders[-1]
        i = 0
        edge_i = 0
        part_cnt = 0
        n_parts = len(wall_borders) // 2

        while i < len(wall_borders):
            if use_fingers:
                if part_cnt % 2:
                    left, right = lf, rf
                else:
                    if part_cnt == n_parts - 1:
                        left, right = lF, rf
                    else:
                        left, right = lF, rF
                if angle == 0:
                    left = self.edges["d"]
                leftsettings.setValues(self.thickness, angle=angle)
            else:
                left = right = self.edges["e"]

            length = wall_borders[i] - length_correction
            angle = wall_borders[i + 1]

            if use_fingers:
                rightsettings.setValues(self.thickness, angle=angle)
                if angle == 0:
                    right = self.edges["D"]
            if angle < 0:
                length_correction = self.thickness * math.tan(
                    math.radians(-angle / 2))
            else:
                length_correction = 0.0
            length -= length_correction

            bottom_e = self._mateEdge(edge_i) if mate_bottom else self.edges["e"]
            top_e = self._mateEdge(edge_i) if mate_top else self.edges["e"]
            self.rectangularWall(
                length, h, [bottom_e, right, top_e, left], move="right")

            i += 2
            edge_i += 1
            part_cnt += 1

    def render(self):
        points = self.points
        if isinstance(points, str):
            points = argparsePoints(points)

        points = self._ensureCCW(points)
        t = self.thickness

        if self.outside:
            points = vectors.kerf(points, -t)
            # Size wall height from the actual top/bottom edge widths.
            # tslot_on=walls uses protruding tabs (margin=inner_offset);
            # tslot_on=panels uses plain/mate edges (no protrusion) so h stays
            # the full outside height.
            e1 = False if self.bottom == "none" else self.edges.get(
                self._wallTBEdge(self.bottom))
            e2 = False if self.top == "none" else self.edges.get(
                self._wallTBEdge(self.top))
            self.h = self.adjustSize(self.h, e1, e2)

        self.poly_points = points
        self.borders = self.pointsToBorders(points)
        self.lid_borders = self.pointsToBorders(
            vectors.kerf(points, t))

        # With T-slots, side walls sit inset from the panel outer edge so the
        # panel closes the T openings. Wall lengths follow the inset polygon.
        if self.join == "tslot":
            inset = self.edges["w"].settings.inner_offset
            wall_points = vectors.kerf(points, -inset)
            if len(wall_points) < 3:
                raise ValueError(
                    "T-slot inner_offset is too large for this polygon; "
                    "walls would collapse")
            self.wall_borders = self.pointsToBorders(wall_points)
        else:
            self.wall_borders = self.borders

        with self.saved_context():
            self._drawPanel(self.bottom, move="right")
            self._drawPanel(self.top, move="right")

        panel_e = self._panelEdge()
        self.polygonWall(self.borders, edge=panel_e, move="up only")
        self.moveTo(0, t)

        bottom = self._wallTBEdge(self.bottom)
        top = self._wallTBEdge(self.top)

        if self.join == "tslot" and self.tslot_on == "panels":
            # Panels carry T-slots; walls get aligned counterpart holes.
            # Do not gate on bottom/top edge chars: those are "e" in this mode.
            mate_bottom = self.bottom != "none"
            mate_top = self.top != "none"
            if mate_bottom or mate_top:
                self._polygonWallsTSlotMate(
                    self.wall_borders, self.h, mate_bottom, mate_top)
            else:
                self._polygonWallsStraight(
                    self.wall_borders, self.h, bottom, top)
        elif self.wall_joints == "none":
            self._polygonWallsStraight(self.wall_borders, self.h, bottom, top)
        else:
            self.polygonWalls(
                self.wall_borders, self.h, bottom=bottom, top=top)
