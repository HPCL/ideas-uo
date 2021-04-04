# Git repository mining and analysis software

The collection of packages in this repository are developed as part of the 
DOE [IDEAS-ECP](https://ideas-productivity.org/) project on high-performance software 
development productivity. 

The `code` subdirectory includes various utilities for git repository data acquisition 
and database client code with examples. 

The `patterns` and `sandbox` directories include example analyses using git commits data, 
github or gitlab issues, and developer emails. Many of these were inspired by the 
short [book](https://www.pluralsight.com/content/dam/pluralsight2/landing-pages/offers/flow/pdf/Pluralsight_20Patterns_ebook.pdf) 
by Plurasight on "20 patterns to watch for in your engineering team".

## Getting started
You can take a look at the [notebooks](notebooks) to try out and learn what you can do with this tool. 
Some of them have been made available through Google Colab, so you don't have to install anything to try them out.

Note that this set of tools is still under very active development, so at any point 
some functionality may not work as expected. The basic requirements are Python 3
.9 or newer and the `pip` package manager.

It is best to set up a new python3 environment first; complete instructions can be 
found [here](https://docs.python.org/3/library/venv.html). 
Once you have created and activated the environment, you can install prerequisites with 
`pip install -r requirements.txt`.

If you wish to run the notebooks locally, you need to have jupyter (`pip install jupyter`) 
or jupyter-lab (`pip install jupyterlab`), 
and you also must install the ideas-uo python packages first 
(or, instead of installing, you can simply add the full path to `ideas-uo/src` to your `PYTHONPATH` environment variable). 
To install the package
locally, use the `pip install -e .` command in the top-level project directory. 
Then you can run `jupyter-lab` or `jupyter`
in the `ideas-uo` directory. You can also open a specific notebook, 
e.g., `jupyter-lab notebooks/PatternsTest.ipynb`
 
In order to access the database containing project information, you also need to have 
a MySQL client library installed on your system before installing the requirements with `pip`. 
This requires that you install the mysql client library on your system first. On
Ubuntu 20.04, for example, you can accomplish this with `sudo apt install python3.9-dev libmysqlclient-dev`.


## Testing

To run the provided tests, first ensure your python environment includes the packages 
in `requirements.txt`, then in the top-level repository directory `ideas-uo`, run
```
python -m pytest -v
```
To run the tests in a specific subdirectory, simply add the path to the above command.
