# Website __development__ setup instructions

## Setting the python environment

### Create a python virtual environment
`python3 -m venv env`

### Activate it

For Windows:
`env\Scripts\activate.bat`

For Unix or MacOs:
`source env/bin/activate`

## Installing dependencies

`pip install -r requirements.txt`

## Run the development server

within the `./website` folder run: `python manage.py runserver`

