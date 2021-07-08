FROM jupyter/minimal-notebook:ubuntu-20.04

# docker build -t ideas-uo .

# The base image has changed the active user to jovyan
USER root
RUN apt-get update && apt-get install -y libmysqlclient-dev gcc

# Install ideas-uo
WORKDIR /home/jovyan/work
COPY . /home/jovyan/work
RUN pip install -r requirements.txt && pip install -e . && chown -R jovyan .

# Return to original notebook user
USER jovyan
