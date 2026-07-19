
FORK OF https://github.com/florianfesti/boxes.py
================================================
This fork: https://github.com/TobyKLight/boxes

Customised for a specific project:

- **IrregularBox** — polygon box generator. Enter arbitrary XY vertices
  (space-separated ``x,y`` pairs in mm). Only tested with simple convex
  polygons. A square or other simple shape works fine if you enter its
  corners as points.
- **T-slot joints** for IrregularBox generator only, as an alternative
  to finger joints on the panels to wall sides. (The wall sides can have finger joints or no joints)

How to download and run for non-coders 
-----------------------------------------------------

1. If you don't have it install **Python 3** from https://www.python.org/downloads/
   (on Windows, tick “Add python.exe to PATH” during setup).
2. Open this page in a browser:
   https://github.com/TobyKLight/boxes
3. Click the green **Code** button → **Download ZIP**. Unzip the folder
   somewhere convenient (e.g. your Desktop).
4. Open a terminal in that unzipped folder
5. Install the python project dependencies 

.. code-block:: rst

    pip install -e


6. Start the local web UI::

.. code-block:: rst

    boxesserver


7. Open http://localhost:8000 in your browser. Under **Box**, open
   **IrregularBox**. Change settings and generate SVG for your laser
   cutter. Stop the server with Ctrl+C in the terminal.

New functions
---------------------------------

In IrregularBox Settings:

- **join** — ``finger`` (classic finger joints) or ``tslot`` (T-slots +
  support tabs). Default: ``tslot``.
- **tslot_on** — which face gets the T-cutouts (the other face gets the
  mating tab slots + bolt holes):

  - ``panels`` — T-slots on top/bottom panels (default)
  - ``walls`` — T-slots on the vertical side walls

- **wall_joints** — how vertical wall corners meet: ``finger`` or
  ``none`` (butt joints). Independent of panel↔wall join style.
- **points** — polygon outline, e.g. ``0,0 120,0 100,80 20,70``

T-Slot Settings 
-----------------------------------------------

These are in mm 

- **bolt** (5.0) — bolt shaft diameter
- **nut_width** (7.5) / **nut_height** (3.0) — nut pocket across flats /
  along the shaft
- **shaft_length** (12.0) — how deep the T goes from the original joining
  surface
- **nut_offset** (7.0) — distance from that surface to the start of the
  nut pocket
- **allow_cropped** — if an edge is too short for a full T-unit, allow one
  scaled unit

These are relative multipliers of material thickness

- **inner_offset** (1.0) — how far the wall body sits inset from the
  original joining surface; tabs reach back out to that surface; the
  panel closes the T openings. Play with it is the easiest way to see what it does. 
- **tab_offset** (2.5) — centre-to-centre from bolt/T to each support tab
- **tab_width** (2.0) — width of each support tab
- **safe** (1.0) — margin outside each tab within a unit

Other changes 
- **fixed_line_width** (Default Settings, on by default) — In the original project setting a low burn also made very thin lines visually. 
   With this on Burn still offsets the cut geometry for kerf; this only affects how thick lines look on
  screen / in the file.
- updated the boxesserver to work better on windows including shut down properly when you press ctrl-c 


## ORIGINAL README BELOW ##
======
About Boxes.py
==============

+----------------------------------------------+----------------------------------------------+----------------------------------------------+----------------------------------------------+----------------------------------------------+
| .. image:: static/samples/NotesHolder.jpg    | .. image:: static/samples/OttoBody.jpg       | .. image:: static/samples/PaintStorage.jpg   | .. image:: static/samples/ShutterBox.jpg     | .. image:: static/samples/TwoPiece.jpg       |
+----------------------------------------------+----------------------------------------------+----------------------------------------------+----------------------------------------------+----------------------------------------------+

* Boxes.py is an online box generator

  * https://boxes.hackerspace-bamberg.de/

* Boxes.py is an Inkscape plug-in
* Boxes.py is library to write your own
* Boxes.py is free software licensed under GPL v3+
* Boxes.py is written in Python and runs with Python 3

Boxes.py comes with a growing set of ready-to-use, fully parametrized
generators. See https://florianfesti.github.io/boxes/html/generators.html for the full list.

+----------------------------------------------+----------------------------------------------+----------------------------------------------+
| .. image:: static/samples/AngledBox.jpg      | .. image:: static/samples/FlexBox2.jpg       | .. image:: static/samples/HingeBox.jpg       |
+----------------------------------------------+----------------------------------------------+----------------------------------------------+

Features
--------

Boxes.py generates SVG images that can be viewed directly in a web browser but also
postscript and - with pstoedit as external helper - other vector formats
including dxf, plt (aka hpgl) and gcode.

Of course the library and the generators allow selecting the "thickness"
of the material used and automatically adjusts lengths and width of
joining fingers and other elements.

The "burn" parameter compensates for the material removed by the laser. This
allows fine tuning the gaps between joins up to the point where plywood
can be press fitted even without any glue.

Finger Joints are the work horse of the library. They allow 90° edges
and T connections. Their size is scaled up with the material
"thickness" to maintain the same appearance. The library also allows
putting holes and slots for screws (bed bolts) into finger joints,
although this is currently not supported for the included generators.

Dovetail joints can be used to join pieces in the same plane.

Flex cuts allows bending and stretching the material in one direction. This
is used for rounded edges and living hinges.

+----------------------------------------------+----------------------------------------------+----------------------------------------------+
|   .. image:: static/samples/TypeTray.jpg     |     .. image:: static/samples/BinTray.jpg    | .. image:: static/samples/DisplayShelf.jpg   |
+----------------------------------------------+----------------------------------------------+----------------------------------------------+
| .. image:: static/samples/AgricolaInsert.jpg | .. image:: static/samples/HeartBox.jpg       | .. image:: static/samples/Atreus21.jpg       |
+----------------------------------------------+----------------------------------------------+----------------------------------------------+

Documentation
-------------

Boxes.py comes with Sphinx based documentation for usage, installation
and development.

The rendered version can be viewed at <https://florianfesti.github.io/boxes/html/index.html>.
