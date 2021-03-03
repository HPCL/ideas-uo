#!/bin/bash

source /Users/norris/python_environments/ideas-uo/bin/activate
# After saving the
#projects="spack lammps petsc Nek5000 E3SM qmcpack qdpxx LATTE namd fast-export enzo-dev tau2 xpress-apex nwchem"
projects="spack lammps petsc Nek5000 E3SM qmcpack qdpxx LATTE namd fast-export enzo-dev tau2 xpress-apex"

if [ ! -d tmp ]; then mkdir tmp; fi
sed -ie "s|project_name=[\"'].*[\"']|project_name=sys.argv[1]|" PatternsTest.py

for project in $projects ; do
  echo ">>>>>>> PatternsTest $project"
  sed -e "s|project_name='.*'|project_name='$project'|" PatternsTest.ipynb > $project-PatternsTest.ipynb
  ####python ./PatternsTest.py $project
  jupyter nbconvert --to html --execute $project-PatternsTest.ipynb
  mv $project-PatternsTest.ipynb tmp/
  mv $project-PatternsTest.html html/
done
