#!/bin/bash
# To provide a list of project names, run with ./run.sh -p "proj1 proj2 ..."
# To provide the database password: ./run.sh -pwd passwordstring
# Or with both options: ./run.sh -p "proj1 proj2 ..."  -pwd passwordstring

# nwchem works, but takes a long time, so we don't include it in the regular refresh
projects="spack lammps petsc Nek5000 E3SM qmcpack qdpxx LATTE namd fast-export enzo-dev tau2 xpress-apex" # nwchem"
pwd=""
while true; do
  case "$1" in
    -p | --projects) projects="$2"; shift 2 ;;
    -pwd ) pwd="$2"; shift 2 ;;
    -- ) shift; break ;;
    * ) break ;;
  esac
done
echo "Projects: $projects";
echo "Password: $pwd";

if [ ! -d tmp ]; then mkdir tmp; fi
# Create a simple python script version of the notebook(s)
jupyter nbconvert --to script PatternsTest.ipynb
sed -ie "s|project_name=[\"'].*[\"']|project_name=sys.argv[1]|" PatternsTest.py

for project in $projects ; do
  echo ">>>>>>> PatternsTest $project"
  sed -e "s|project_name='.*'|project_name='$project'|" -e "s|get_data(.*)|get_data(dbpwd='$pwd')|" PatternsTest.ipynb > $project-PatternsTest.ipynb
  ####python ./PatternsTest.py $project
  jupyter nbconvert --to html --execute $project-PatternsTest.ipynb
  mv $project-PatternsTest.* tmp/
done

if [ "$USER" == "norris" ]; then
   rsync -avz tmp/*.html ix:public_html/ideas-uo/notebooks/html/
fi
