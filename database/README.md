# Database Information

## Directory Structure                   

| Name          | Description                                                         |
| ------------  | ------------------------------------------------------------------- | 
| `django/`     | Django project and corresponding applications for the database.     |
| `examples/`   | Tutorial notebooks on how to access the database.                   |
| `resources/`  | ER diagrams, website description blurbs, and similar files.         |

## Interface Usage

Command line script for updating and adding new projects to the database. This script should be used by just the admins and users should look at the `examples/` on how to access the data. Must be run in the `ideas-uo/` (top level) directory.

#### Updating existing projects:
```bash
python3 -m code.gitutils.db_interface --host HOST --username USERNAME --password PASSWORD --port PORT --database DATABASE --update
```

#### Adding new projects:
```bash
python3 -m code.gitutils.db_interface --host HOST --username USERNAME --password PASSWORD --port PORT --database DATABASE --add_project PROJECT [PROJECT ...]
```

#### Debugging and special flags:

* To check for commits from the beginning (or `--start` flag if specified) and not since the last update use the `--force_epoch` flag.
* To keep repo folders on disk after the script use `--keep_repos`.
* To not fetch branch info (DO THIS FOR DEBUGGING) use `--no_branches`.
* To change the interval of uploads use the `--start` and `--unti` flags. Both take in ISO8601 datetime strings.

## Django/MySQL Notable Changes

| Source File               | Change                                                               |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `IDEAS/IDEAS/settings.py` | Add `'database'` to `INSTALLED_APPS`. Connects database application to the project. Does not automatically occur when running `migrate.py`. |
| `IDEAS/IDEAS/settings.py` | May want to change `SECRET_KEY` once closer to use.                                                                                         |
| `IDEAS/IDEAS/settings.py` | Under `DATABASE` set `options` to include: `charset: utf8mb4` and `use_unicode: True`.                                                      |
| `MySQL Tables & Database` | Need to alter database and tables to collate to `utf8mb4` charset.                                                                          |
