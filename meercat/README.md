# Website setup

1. Create a python virtual environment
`python3 -m venv env`

2. Activate it

For Windows:
`env\Scripts\activate.bat`

For Unix or MacOs:
`source env/bin/activate`

3. Install python dependencies

`pip install -r requirements.txt`

4. Run the development server

Within the `./website` folder run: `python manage.py runserver`

5. Copy the .env file located in the server within the meercat directory

The .env file is not in GitHub