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

4. Bundle js and css

    1. Install package.json dependencies
        
    Within `./website/static` run `npm install`

    2. Bundle
    
    Within `./website/static` run `npm run build`

5. Run the development server

Within the `./website` folder run: `python manage.py runserver`
