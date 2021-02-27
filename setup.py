#!/usr/bin/env python

from distutils.core import setup

setup(name='ideas-uo',
      version='0.1.0',
      description='Git repository mining utilities',
      author='IDEAS ECP Team at University of Oregon',
      author_email='norris@cs.uoregon.edu',
      package_dir={'': 'src'},
      packages=['gitutils','patterns'],
     )
