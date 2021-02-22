# Database Information

## Directory Structure                   

| Name          | Description                                                         |
| ------------  | ------------------------------------------------------------------- | 
| `django/`     | Django project and corresponding applications for the database.     |
| `examples/`   | Tutorial notebooks on how to access the database.                   |
| `interface/`  | Script for interfacing with database. Use this file in your script. |
| `resources/`  | ER diagrams, website description blurbs, and similar files.         |

## Interface Usage

Command line script for updating and adding new projects to the database. This script should be used by just the admins and users should look at the `examples/` on how to access the data.

#### Updating existing projects:
```bash
./db_interface.py --host HOST --username USERNAME --password PASSWORD --port PORT --database DATABASE --update
```

#### Adding new projects:
```bash
./db_interface.py --host HOST --username USERNAME --password PASSWORD --port PORT --database DATABASE --add_project PROJECT [PROJECT ...]
```

#### Debugging and special flags:

To check for commits from the beginning and not since the last update use the `--force_epoch` flag.
To keep repo folders on disk after the script use `--keep_repos`.
To not fetch branch info (DO THIS FOR DEBUGGING) use `--no_branches`.

## Django/MySQL Notable Changes

| Source File               | Change                                                               |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `IDEAS/IDEAS/settings.py` | Add `'database'` to `INSTALLED_APPS`. Connects database application to the project. Does not automatically occur when running `migrate.py`. |
| `IDEAS/IDEAS/settings.py` | May want to change `SECRET_KEY` once closer to use.                                                                                         |
| `IDEAS/IDEAS/settings.py` | Under `DATABASE` set `options` to include: `charset: utf8mb4` and `use_unicode: True`.                                                      |
| `MySQL Tables & Database` | Need to alter database and tables to collate to `utf8mb4` charset.                                                                          |
