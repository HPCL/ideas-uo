import sys, os, getpass, warnings
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.append(os.path.join(os.getcwd(), "..", "src"))
from patterns.visualizer import Visualizer

project = "ideas-uo"
vis = Visualizer(project_name=project)
vis.get_data()

removed = vis.remove_external()
vis.hide_names = False
if not ("unique_author" in vis.commit_data.columns):
    vis.set_unique_authors()

""" vis.commit_data columns: 
['sha', 'branch', 'datetime', 'author', 'email', 'message', 'filepath',
       'diff', 'year', 'month', 'day', 'doy', 'dow', 'diff_summary',
       'locc-basic', 'locc', 'locc-', 'locc+', 'change-size-cos',
       'unique_author']
"""
# Create author df containing just filenames
author_df = vis.commit_data[["filepath", "unique_author"]].reset_index().copy()
author_df["commit_counts"] = 1

# Count commits per author per file
commits = author_df.groupby(["filepath", "unique_author"]).sum().reset_index()
# print(commits.head())

commits["total_commits"] = commits.groupby("filepath")["commit_counts"].transform("sum")
commits.reset_index()
# print(commits)

# Compute a simple authorship metric based on commits
commits["degree_commits"] = commits["commit_counts"] / commits["total_commits"]
print("\n>>> Degree of authorship based on commits:")
print(commits.sort_values(by=["degree_commits"], ascending=False))

print("\n>>> Authors with DOA>0.75 per file:")
doa_commits_df = (
    commits[commits["degree_commits"] >= 0.75]
    .groupby("filepath")
    .agg({"unique_author": ",".join})
    .sort_values(by=["unique_author"], ascending=False)
)
doa_commits_df.reset_index()
print(doa_commits_df)

# Next, compute a simple authorship metric based on lines of code and cos difference
author_df = (
    vis.commit_data[["filepath", "unique_author", "locc-basic", "change-size-cos"]]
    .reset_index()
    .copy()
)

# Accumulate changes per author per file
locc_counts = (
    author_df.groupby(["filepath", "unique_author"])
    .agg({"locc-basic": "sum", "change-size-cos": "sum"})
    .reset_index()
)

# Normalize changes per author per file (make them relative to totals per file)
locc_counts["total_locc"] = locc_counts.groupby("filepath")["locc-basic"].transform(
    "sum"
)
locc_counts["degree_locc"] = locc_counts["locc-basic"] / locc_counts["total_locc"]

locc_counts["total_cosdiff"] = locc_counts.groupby("filepath")[
    "change-size-cos"
].transform("sum")
locc_counts["degree_cosdiff"] = (
    locc_counts["change-size-cos"] / locc_counts["total_cosdiff"]
)

print("\n>>> Changes per file per author (normalized)\n", locc_counts)

doa_df = (
    commits.merge(locc_counts, on=["filepath", "unique_author"])
    .reset_index()
    .drop(["index"], axis=1)
)
doa_df.to_csv(f"doa-{project}.csv")

print("\n>>> Combined commits, locc, and cosine diff based DOA\n", doa_df)
