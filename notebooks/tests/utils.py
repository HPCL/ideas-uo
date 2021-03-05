import os
from gitutils.utils import err
from patterns.fetcher import Fetcher
from pathlib import Path
cache_dir = os.path.dirname(Path(__file__))

def loadCachedProject(project_name='testrepo'):
    fetcher = Fetcher(project_name)
    fetcher.update_cache_info(cache_dir=cache_dir,cache_file='.testrepo.pickle')
    return fetcher