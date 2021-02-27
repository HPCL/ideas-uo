# Git repository mining and analysis software

The collection of packages in this repository are developed as part of the DOE [IDEAS](https://ideas-productivity.org/) project on high-performance software development productivity. 

The `code` subdirectory includes various utilities for git repository data acquisition and database client code with examples. 

The `patterns` and `sandbox` directories include example analyses using git commits data, github or gitlab issues, and developer emails.

## Testing

To run the provided tests, first ensure your python environment includes the packages in `requirements.txt`, then in the top-level 
repository directory `ideas-uo`, run
```
python -m pytest -v
```
To run the tests in a specific subdirectory, simply add the path to the above command.
