import sys, os, getpass, warnings
warnings.filterwarnings('ignore')
sys.path.append(os.path.join(os.getcwd(), '..', 'src'))
from patterns.visualizer import Visualizer

project='ideas-uo'
vis = Visualizer(project_name=project)
vis.get_data()

removed = vis.remove_external()
vis.hide_names = False
if not ('unique_author' in vis.commit_data.columns):
    vis.set_unique_authors()

""" vis.commit_data columns: 
['sha', 'branch', 'datetime', 'author', 'email', 'message', 'filepath',
       'diff', 'year', 'month', 'day', 'doy', 'dow', 'diff_summary',
       'locc-basic', 'locc', 'locc-', 'locc+', 'change-size-cos',
       'unique_author']
"""
# Create author df containing just filenames
author_df = vis.commit_data[['filepath', 'unique_author']].reset_index().copy()
author_df['commit_counts'] = 1

# Count commits per author per file
author_counts = author_df.groupby(['filepath', 'unique_author']).sum().reset_index()
#print(author_counts.head())

author_counts['total_commits'] = author_counts.groupby('filepath')['commit_counts'].transform('sum')
author_counts.reset_index()
#print(author_counts)

# Compute a simple authorship metric based on commits
author_counts['degree'] = author_counts['commit_counts'] / author_counts['total_commits']
print("\n>>> Degree of authorship based on commits:")
print(author_counts.sort_values(by=['degree'], ascending=False))

print('\n>>> Authors with DOA>0.75 per file:')
doa_df = author_counts[author_counts['degree']>=0.75].groupby('filepath').agg({'unique_author': ','.join}).sort_values(by=['unique_author'], ascending=False)
doa_df.reset_index()
print(doa_df)
doa_df.to_csv(f'doa-{project}.csv')

# Next, compute a simple authorship metric based on lines of code and cos difference
author_df = vis.commit_data[['filepath', 'unique_author', 'locc-basic', 'change-size-cos']].reset_index().copy()

# Accumulate changes per author per file
locc_counts = author_df.groupby(['filepath', 'unique_author']).agg({'locc-basic': 'sum', 'change-size-cos': 'sum'}).reset_index()
print("\n>>> Changes per file per author\n",locc_counts)
