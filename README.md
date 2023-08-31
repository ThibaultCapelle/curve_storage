
# Curve Storage: a database to store, find and save efficiently scientific datasets

This is a small python library made to interact with a PostGreSQL database server, used to store the metadatas of some curves that are stored somewhere. It comprises a GUI that allows easy visualisation, filtered search, fitting and deletion/editing of curves. 

## Installation

First you need a running PostgreSQL server. For a detailed description of how to install PostgreSQL and launch a server, see https://www.postgresql.org/docs/current/admin.html


After this, to install the library, open a command line after having installed git, then go to the repository you want to store it, then do: 

```bash
git clone http://gitea.qmpl.xyz/ThibaultCapelle/curve_storage.git 

cd curve_storage 

pip install psycopg2 pyqtgraph==0.11.0 

pip install –e . 
```
 Then open a python console, and type: 
```python
from curve_storage.database import SQLDatabase 

SQLDatabase.set_config() 
```

### Basic use
To create a cuvre, simply enter:
```python
from curve_storage.database import Curve
curve=Curve(x_data, y_data, name='example', project='example_project',
 sample='example_sample', extra_param_name='example_value')
 ```
Each curve has two numpy arrays, assumed to be complex, which represents usually the x and y values to store, as well as a dictionnary with various parameters, here the extra_param_name, but it can be a lot of them. On top of it, it has special params linked to the database and which therefore can be searched with filters: a unique id, a name, a sample, a project and a date. It also has a dedicated folder that can be used, as well as a hierarchical system: each curve can have a parent and multiple childs.

The curves can be searched and addressed easily with the GUI, than you can call with:
```python
from curve_storage import gui
 ```
 This opens the following window:
 <p>
    <a >
        <img src="./doc/pictures/GUI.jpg">
    </a>
</p>

on the left (1) side you can see the curves that match the query, as well as some options to edit this query. The selected curve data are dispayed in the center (2) window, in the fomat chosen with the top panel. The right (3) panel displays the parameters of the selected curve, and the bottom (4) panel shows some additional options: - the comment associated ith each curve, that can be edited and saved, the fitting options, that use the x data selected y the data viewer, and the default plot figure options, which are used to save a default plot of the viewed data.
