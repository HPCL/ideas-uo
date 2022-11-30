# Website setup

1. Create a python virtualenv virtual environment
	1. Install virtualenv via pipx `pipx install virtualenv` (recommended by cirtualenv documentation) or via pip `python -m pip install --user virtualenv
	2. Create a virtual environment `virtualenv env`

2. Activate it

    For Windows: `env\Scripts\activate.bat`

    For Unix or MacOs: `source env/bin/activate`

3. Install python dependencies

    `pip install -r requirements.txt`

4. Run the development server

    Within the `./website` folder run: `python manage.py runserver`

5. Copy the .env file located in the server within the meercat directory

    The .env file is not in GitHub

6. Place credentials.ini in the folder above meercat

7. Update meercat/website/settings.py to use the correct database.
   
	Example:   
		DATABASES = {
		    'default': {
		        'ENGINE': 'django.db.backends.mysql',
		        'NAME': 'ideas_db',
		        'HOST': '/var/run/mysqld/mysqld.sock',
		        'PORT': '3331',
		        'USER': 'ideas_admin',
		        'PASSWORD': '*********',
		        'OPTIONS': {'charset': 'utf8mb4',
		                    'use_unicode': True},
		    }
		}

8. Update the following configurations in meercat/website/settings.py
	1. The location of the json configuraion file for meercat when it is opened. The json file is currently called `meercat.config.json` and is in the BASE_DIR directory.

	2. The REPOS_DIR setting. This setting is the directory awhere all repositories analyzed by meercat are located.

9. Install codemirror js/css files to meercat/static/codemirro/lib

	codemirror.js
	codemirror.css

