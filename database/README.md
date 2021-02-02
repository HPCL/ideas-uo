# Database Information

## Directory Structure                   

| Name          | Description                                                         |
| ------------  | ------------------------------------------------------------------- | 
| `django/`     | Django project and corresponding applications for the database.     |
| `examples/`   | Tutorial notebooks on how to access the database.                   |
| `interface/`  | Script for interfacing with database. Use this file in your script. |
| `resources/`  | ER diagrams, website description blurbs, and similar files.         |

## Interface Usage

***NOT YET READY***
Built to run on Google Colab (Python 3.6.9). Make sure the packages in `interface/requirements.txt` are installed. Then copy all the python files in `interface/` to your current working directory. 

```python

from db_interface import DatabaseInterface

# Add/update a git project.
interface = DatabaseInterface()
url = 'https://github.com/HPCL/ideas-uo.git'
interface.add_project(url)
```

## Django Notable Changes

| Source File               | Change                                                               |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `IDEAS/IDEAS/settings.py` | Add `'database'` to `INSTALLED_APPS`. Connects database application to the project. Does not automatically occur when running `migrate.py`. |
| `IDEAS/IDEAS/settings.py` | May want to change `SECRET_KEY` once closer to use.                                                                                         |

