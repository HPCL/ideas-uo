# Git repository mining and analysis software

The collection of packages in this repository are developed as part of the
DOE [IDEAS-ECP](https://ideas-productivity.org/) project on high-performance software
development productivity. The GremCat set of tools is part of the larger
[CAT-SDK](https://github.com/CAT-SDK) collection of git and related mining and analysis software infrastructure.

The `code` subdirectory includes various utilities for git repository data acquisition
and database client code with examples.

The `patterns` and `sandbox` directories include example analyses using git commits data,
github or gitlab issues, and developer emails. Many of these were inspired by the
short [book](https://www.pluralsight.com/content/dam/pluralsight2/landing-pages/offers/flow/pdf/Pluralsight_20Patterns_ebook.pdf) by Plurasight on "20 patterns to watch for in your engineering team".

## Getting started

### Notebooks on Google Colab

You can take a look at the [notebooks](notebooks) to explore the data and the current mining functionality.
Some of them have been made available through Google Colab, so you don't have to install anything locally to try them out.

### Install

In order to access the database containing project information, you also need to have
a MySQL client library installed on your system before installing the requirements with `pip`.
This requires that you install the mysql client library on your system first (`mysql_config` should be in your path). On
Ubuntu 20.04 or later, for example, you can accomplish this with `sudo apt install python3.9-dev libmysqlclient-dev`. On MacOS, you can use `brew install mysql-client`.

Next, create a new python3 environment in which GremCat will be installed and used; complete instructions can be found [here](https://docs.python.org/3/library/venv.html). For example:

```bash
python3 -m venv env-gremcat
source ./env-gremcat/bin/activate
```

Once you have created and activated the environment, you can install prerequisites with
``pip install -r requirements.txt``

### Local Notebooks

Note that this set of tools is still under very active development, so at any point
some functionality may not work as expected. The basic requirements are Python 3
.9 or newer and the `pip` package manager.

If you wish to run the notebooks locally, you need to have jupyter (`pip install jupyter`)
or jupyter-lab (`pip install jupyterlab`),
and you also must install the ideas-uo python packages first
(or, instead of installing, you can simply add the full path to `ideas-uo/src` to your `PYTHONPATH` environment variable).
To install the package
locally, use the `pip install -e .` command in the top-level project directory.
Then you can run `jupyter-lab` or `jupyter`
in the `ideas-uo` directory. You can also open a specific notebook,
e.g., `jupyter-lab notebooks/PatternsTest.ipynb`

### Container

If you want to get started with using the software without modifying your system,
you can use the provided [Dockerfile](Dockerfile) to build a base container with
all dependencies installed.

```bash
$ docker build -t ideas-uo .
```

The contents of the repository here (meaning the notebook examples) will be copied
to the active user's work directory (/home/joyvan/work) so you can run the container
without needing to bind content locally:

```bash
$ docker run --rm -p 8888:8888 ideas-uo
```

When you run the command above, a link will be pasted in the terminal (with a token included)
that you can copy paste into your browser to see the interface. If you want
to instead bind the present working notebooks directory (and files you can make changes to
that will persist) you can instead run the container as follows:

```bash
$ docker run --rm -p 8888:8888 -v "${PWD}/notebooks":/home/user/work/notebooks ideas-uo
```

## Testing

To run the provided tests, first ensure your python environment includes the packages
in `requirements.txt`, then in the top-level repository directory `ideas-uo`, run

```
python3 -m pytest -v
```

To run the tests in a specific subdirectory, simply add the path to the above command.

## To add a project to the repository:

Here is an example to add a project (in this case, hypre) to the database server sansa.cs.uoregon.edu (mysql). In the directory containing the ideas-uo repository clone:

```
$ python3 -m src.gitutils.db_interface --host sansa.cs.uoregon.edu --username ideas_admin --password <IDEAS_ADMIN_PWD> --port 3331 --database ideas_db --add_project "https://github.com/hypre-space/hypre.git"
```
