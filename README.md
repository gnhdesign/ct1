Coffee table CT1 is a parametric cadquery/cqparts model of a coffeetable.

Read more about the design on my website https://www.gntech.se/en/projects/ct1/
Or order your own coffee table here https://www.gnhdesign.se

A prerequiste is to have FreeCAD installed.

The easiest way to build and view the model is to use the [freecad-cadquery-module](https://github.com/jmwright/cadquery-freecad-module) which can be installed through FreeCAD's Addon manager.

Then you open the script in the cadquery-menu and press F2 to build.

Alternatively you can build the model from commandline, first you need to install [cadquery](https://github.com/dcowden/cadquery) and [cqparts](https://github.com/fragmuffin/cqparts).

```
pip install --user cadquery
pip install --user cqparts
```

Then you can run the script with python. The design will open in a webviewer.

```
python ct1.py
```
