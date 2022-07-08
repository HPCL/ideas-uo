FROM jupyter/minimal-notebook:ubuntu-20.04 as Helios 

# docker build -t ideas-uo .

# The base image has changed the active user to jovyan
USER root
RUN apt-get update && apt-get install -y libmysqlclient-dev gcc

# Install ideas-uo
WORKDIR /home/jovyan/work
COPY . /home/jovyan/work
RUN pip install pytest && \
    pip install jupyter && \
    pip install requests && \
    pip install pandas && \ 
    pip install matplotlib && \ 
    pip install seaborn && \ 
    pip install plotly && \ 
    pip install plotly-express && \ 
    pip install textdistance && \
    pip install python-Levenshtein && \ 
    pip install networkx && \ 
    pip install pydot && \ 
    pip install graphviz && \ 
    pip install bs4 && \ 
    pip install arrow && \ 
    pip install mysqlclient && \ 
    pip install fuzzywuzzy && \ 
    pip install ply

# && pip install -e .. && chown -R jovyan ..

# Return to original notebook user
# USER jovyan

ARG PROJECT_NAME 

ENV project_name=${PROJECT_NAME}

CMD /bin/bash 