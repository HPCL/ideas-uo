import sys, os, getpass, warnings
warnings.filterwarnings('ignore')
sys.path.append(os.path.join(os.getcwd(), '..', 'src'))
from patterns.visualizer import Visualizer

vis = Visualizer(project_name='ideas-uo')
vis.get_data()

removed = vis.remove_external()
vis.hide_names = False
if not ('unique_author' in vis.commit_data.columns):
    vis.set_unique_authors()

# Create author df containing just filenames
author_df = vis.commit_data[['filepath', 'unique_author']].reset_index().copy()
author_df['commit_counts'] = 1

# Count commits per author per file
author_counts = author_df.groupby(['filepath', 'unique_author']).sum().reset_index()
#print(author_counts.head())

author_counts['total_commits'] = author_counts.groupby('filepath')['commit_counts'].transform('sum')
author_counts.reset_index()
#print(author_counts)

# Compute degree of authorship
author_counts['degree'] = author_counts['commit_counts'] / author_counts['total_commits']
print("Degree of authorship based on commits:")
print(author_counts.sort_values(by=['degree'], ascending=False))

print('Number of authors with >= 0.75 degree of authorship:', len(author_counts[author_counts['degree'] > 0.5]))
doa_df = author_counts[author_counts['degree']>=0.75].groupby('filepath').agg({'unique_author': 'count'}).sort_values(by=['unique_author'], ascending=False)
doa_df.reset_index()
print(doa_df)
