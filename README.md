# Git repository mining and analysis software

The collection of packages in this repository are developed as part of the 
DOE [IDEAS](https://ideas-productivity.org/) project on high-performance software 
development productivity. 

The `code` subdirectory includes various utilities for git repository data acquisition 
and database client code with examples. 

The `patterns` and `sandbox` directories include example analyses using git commits data, 
github or gitlab issues, and developer emails. Many of these were inspired by the 
short [book](https://www.pluralsight.com/content/dam/pluralsight2/landing-pages/offers/flow/pdf/Pluralsight_20Patterns_ebook.pdf) 
by Plurasight on "20 patterns to watch for in your engineering team".

## Getting started
Note that this set of tools is still under very active development, so at any point 
some of the functionality may not work as expected. The basic requirements are Python 3
.6 or newer and the `pip` package manager.

It is best to set up a new python3 environment first; complete instructions can be 
found [here](https://docs.python.org/3/library/venv.html). 
Once you have created and activated the environment, you can install prerequisites with 
`pip install -r requirements.txt`.

To check your environment, run the tests as described in the _Testing_ section below.

If you wish to install the code portions of the repository, you can use the `pip install
 -e .` command in the top-level project directory.
 
In order to access the database containing project information, you also need to have 
a MySQL client library installed on your system, as well as the `mysqlclient` python
 module.

## Testing

To run the provided tests, first ensure your python environment includes the packages 
in `requirements.txt`, then in the top-level repository directory `ideas-uo`, run
```
python -m pytest -v
```
To run the tests in a specific subdirectory, simply add the path to the above command.
