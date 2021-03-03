#!/bin/bash

# After saving the
projects="spack lammps petsc Nek5000 E3SM qmcpack qdpxx LATTE namd fast-export enzo-dev nwchem"
#projects="spack lammps petsc Nek5000 E3SM qmcpack qdpxx LATTE namd fast-export enzo-dev"

if [ ! -d tmp ]; then mkdir tmp; fi
sed -ie "s|project_name=[\"'].*[\"']|project_name=sys.argv[1]|" PatternsTest.py

for project in $projects ; do
  echo ">>>>>>> PatternsTest $project"
  sed -e "s|project_name=[\"'].*[\"']|project_name='$project'|" PatternsTest.ipynb > tmp/$project-PatternsTest.ipynb
  #jupyter nbconvert --to html tmp/$project-PatternsTest.ipynb --output tml/$project-PatternsTest.html
  python ./PatternsTest.py $project
done
