import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# import nltk
import seaborn as sns

sns.set(font_scale=1.5)
import re
from collections import Counter
import math

# from sklearn.feature_extraction.text import TfidfVectorizer
from patterns.fetcher import Fetcher
import textdistance as td
from fuzzywuzzy import process, fuzz

from gitutils.utils import err

WORD = re.compile(r"\w+")


class Diffutils:
    # See https://github.com/life4/textdistance
    diff_algs = {
        "cos": td.cosine,
        "hamming": td.hamming,
        "damerau_levenshtein": td.damerau_levenshtein,
        "jaccard": td.jaccard,
        "jaro": td.jaro,
        "jaro_winkler": td.jaro_winkler,
        "bag": td.bag,
        "editex": td.editex,
    }

    # textdistance.hamming.distance('test', 'text')
    # textdistance.hamming.normalized_distance('test', 'text')

    @staticmethod
    def text_to_vector(text):
        words = WORD.findall(text)
        return Counter(words)


class ProjectConfig:
    """Some project-specific settings can be hardcoded here."""

    aliases = {
        "tau2": {
            "amorris": "Alan Morris",
            "khuck": "Kevin A. Huck",
            "Sameer Shende": "Sameer Suresh Shende",
            "scottb": "Scott Biersdorff",
            "wspear": "Wyatt Joel Spear",
        }
    }
    exclude_subpaths = {
        "tau2": [],
    }


class Patterns(Fetcher):
    weekdays = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    weekday_type = pd.CategoricalDtype(categories=weekdays, ordered=True)

    # edits_summary_re.findall('--++-+-+--++--++-+--') produces ['--++', '-+', '-+', '--++', '--++', '-+']
    edits_summary_re = re.compile(r"(-+\++)")

    # TODO: create per-project configurations, the opposite of .gitignore
    doc_suffixes = ["rst", "md", "txt", "rtf"]
    code_suffixes = [
        "am",
        "awk",
        "bash",
        "bashrc",
        "bat",
        "batch",
        "c",
        "c#",
        "cactus",
        "cc",
        "ccl",
        "cct",
        "charm",
        "cl",
        "cmake",
        "cmd",
        "code",
        "conf",
        "cpp",
        "csh",
        "cshrc",
        "cu",
        "cuh",
        "def",
        "dos",
        "el",
        "f",
        "f77",
        "f90",
        "f95",
        "f03",
        "fc",
        "ff",
        "ffc",
        "fh",
        # BN: Not sure about all of these f90 ones (next 3 lines), but leaving, just in case
        "f90-hide",
        "f90-orig",
        "f90_calhoun",
        "f90_eth1",
        "f90_eth2_failed",
        "f90_exp",
        "f90_future",
        "f90_gamma",
        "f90_helmholtz",
        "f90_hist",
        "f90_incaseof",
        "f90_new",
        "f90_save",
        "f90_sedov",
        "f90_temp",
        "f90_unused",
        "f90_work",
        "ff",
        "h",
        "h-32",
        "h-64",
        "hh",
        "hpp",
        "hxx",
        "java",
        "ksh",
        "lf95",
        "m",
        "pbs",
        "pl",
        "py",
        "r",
        "script",
        "sed",
        "sidl",
        "src",
        "src90",
        "th",
        "tcl",
        "tk",
        "yaml",
        "yml",
    ]

    # These are global, and generally applicable, unless a project-specific list is provided
    excluded_subpaths = ["contrib/", "extern/", "external/"]

    # These are global, and generally applicable, unless a project-specific name is provided
    default_branches = ["/main", "/master", "/develop"]

    @staticmethod
    def is_code(path_str):
        if "." in path_str:
            suffix = path_str.split(".")[-1].lower()
            if suffix in Patterns.code_suffixes:
                return True
        return False

    @staticmethod
    def is_doc(filepath):
        if re.match(r"doc/.*", filepath):
            return True
        elif "." in filepath:
            suffix = filepath.split(".")[-1].lower()
            if suffix in Patterns.doc_suffixes:
                return True
        return False

    def __init__(
        self, project_name=None, project_url=None, exclude_forks=False, forks_only=False
    ):
        super().__init__(project_name, project_url, exclude_forks, forks_only)
        # self.close_session()
        # to store store list of dataframes sorted in descending order by who made the most commits
        self.ranked_by_people = None
        # to store list (file_name, count) sorted by count
        self.ranked_files = None
        # 2d-matrix (dataframe) of developers and files they've touched
        self.developer_file_mat = None
        self.year = None
        self.month = None
        self.year_tup = None
        self.month_tup = None
        self.diff_alg = "cos"
        self.top_developers = None
        self.top_N_map = pd.DataFrame()
        self.authors_data = pd.DataFrame()

    def process_single_commit(self, lines_list):
        # First, create a very brief summary of the changes, e.g., for one set of diffs, produce '--++-+-+--++--++-+--'
        # print(lines_list)
        summary, old, new = "", "", ""
        for line in lines_list:
            #check if line signals whole file change, e.g., move or rename of file.
            if line[:4] in ['+++ ', '--- ']: continue  #skip over file change lines
            if line.startswith("-"):
                summary += "-"
                if len(line)==1:
                  old += ' '  #kind of a kluge. A single - signifies removing a blank line. Using a space to stand in for \n
                else:
                  old += line[1:]  #skip over - char
            elif line.startswith("+"):
                summary += "+"
                if len(line)==1:
                  new += ' '  #kind of a kluge. A single + signifies adding a blank line. Using a space to stand in for \n
                else:
                  new += line[1:]  #skip over + char

        # Update "change" (vs. adding or removing lines), e.g.,  --++ means that two lines are modified, not that
        # two lines are deleted and then two added (line count 2 vs 4).
        # Example input summary: '++----++-+-+--++--++-+--'
        # Example resulting values for removed, added, edited: 4 2 9
        s = summary
        removed, added, edited = 0, 0, 0
        edits = Patterns.edits_summary_re.findall(summary)
        for edit in edits:
            index = s.find(edit)  # next "edit" candidate
            rm, add = s[:index].count("-"), s[:index].count("+")  # non-edits
            ed_rm, ed_add = edit.count("-"), edit.count("+")
            ed = min(
                ed_rm, ed_add
            )  # actual size of edit, basically counts of matching -+ strings
            edited += ed
            removed, added = removed + rm + ed_rm - ed, added + add + ed_add - ed
            s = s[index + len(edit) :]  # advance
        # trailing changes
        removed, added = removed + s.count("-"), added + s.count("+")

        # Total LOCC that takes into acount "edits"
        locc = removed + added + edited

        # Finally, compute the default distance metric
        diff = Diffutils.diff_algs[self.diff_alg].distance(old, new)
        return [summary, len(summary), locc, removed, added, diff]

    def is_external(self, path_str, excluded_paths):
        for path_pattern in excluded_paths:
            if path_str.find(path_pattern) > 0:
                # print('pattern: %s, path: %s' % (path_pattern,path_str))
                return True
        return False

    def set_diff_alg(self, diff_alg="cos", compute=True, recompute=False):
        if diff_alg not in Diffutils.diff_algs.keys():
            print(
                "Warning: you specified an unknown text distance function, available options are %s (more "
                "information can be found at https://github.com/life4/textdistance. Defaulting to cos distance."
                % str(Diffutils.diff_algs.keys())
            )
            diff_alg = "cos"

        self.diff_alg = diff_alg  # To apply: Diffutils.diff_algs[diff_alg].distance (str1, str2), also normalized_distance

        # compute the new diff it not already available:
        if not compute:
            return
        colname = "change-size-%s" % self.diff_alg
        if colname not in self.commit_data.columns:
            compute = True
        if compute or recompute:
            self.commit_data[
                ["diff_summary", "locc-basic", "locc", "locc-", "locc+", colname]
            ] = pd.DataFrame(
                list(
                    self.commit_data["diff"]
                    .str.split(pat="\n")
                    .map(lambda x: self.process_single_commit(x))
                ),
                index=self.commit_data.index,
            )
        self.update_data()

    def annotate_metrics(self, diff_alg="cos"):
        # Add columns with commonly used metrics
        # avoid recomputing the default metrics if they are already there
        if (
            "locc" not in self.commit_data.columns
            or "change-size-%s" % diff_alg not in self.commit_data.columns
        ):
            self.set_diff_alg(diff_alg, compute=True)
        self.update_data()

    def update_data(self):
        return

    def sort_data(self):
        self.commit_data.sort_values(by=["datetime", "sha", "author"], ascending=False)

    def remove_docs(self):
        """Remove all documentation-related files (in place mod)"""
        self.commit_data = self.commit_data[
            self.commit_data["filepath"].map(lambda x: not Patterns.is_doc(x))
        ].reindex()

    def remove_noncode(self):
        """Remove all non-cdoe files (in place mod)"""
        self.commit_data = self.commit_data[
            self.commit_data["filepath"].map(lambda x: Patterns.is_code(x))
        ].reindex()

    def remove_external(self):
        """Attempt to automatically identify external sources and exclude them from analysis"""
        before = self.commit_data.shape[0]
        df = self.commit_data
        if self.project in ProjectConfig.exclude_subpaths.keys():
            ex_paths = ProjectConfig.exclude_subpaths[self.project]
        else:
            ex_paths = Patterns.excluded_subpaths
        self.commit_data = self.commit_data[
            self.commit_data["filepath"].map(
                lambda x: not self.is_external(x, ex_paths)
            )
        ].reindex()
        after = self.commit_data.shape[0]
        if before > after:
            print(
                "INFO: Removed %d external file changes. New total size: %d changes"
                % (before - after, after)
            )
        else:
            print("INFO: No external files found. Total size: %d changes" % after)

    def remove_files(self, files_to_keep):
        """Remove all files from df except the file in the pasted in list"""
        before = self.commit_data.shape[0]
        df = self.commit_data

        self.commit_data = self.commit_data[
            self.commit_data["filepath"].map(lambda x: x in files_to_keep)
        ].reindex()

        after = self.commit_data.shape[0]
        if before > after:
            print(
                "INFO: Removed %d files. New total size: %d changes"
                % (before - after, after)
            )
        else:
            print("INFO: No files found to remove. Total size: %d changes" % after)

    def set_unique_authors(self):
        """ " Use fuzzy matching to identify multiple different names that likely belong to the same developer"""
        print("INFO: Analyzing author names, this can take a few minutes...")
        df = pd.DataFrame(self.commit_data.groupby(["author"])["sha"].count())
        df.reset_index(level=df.index.names, inplace=True)
        df["commits"] = df["sha"]
        df["name_size"] = df["author"].map(lambda x: len(x))
        df = df.sort_values(by=["name_size", "author"], ascending=[False, True])
        df = df[(df["author"] != "") & (df["sha"] != 0)]

        results = {}
        for name in df.author:
            ratio = process.extract(str(name), df.author, limit=10)
            results[name] = ratio
        threshold = 90
        real_names = {}
        count = 0
        done = []
        aliases = {}
        if self.project in ProjectConfig.aliases.keys():
            aliases = ProjectConfig.aliases[self.project]
        for nm, val in results.items():
            # print(nm, ":")
            for entry in val:
                name, score, v = entry
                if name in aliases.keys():
                    real_names[count] = [name, aliases[name]]
                    done.append(name)
                    count += 1
                    continue
                if score < threshold:
                    break
                if name not in done:
                    real_names[count] = [name, nm]
                    done.append(name)
                count += 1
        # Apply manual fixes (when available)

        df2 = pd.DataFrame.from_dict(
            real_names, orient="index", columns=["author", "unique_author"]
        )
        self.authors_data = df.merge(df2, how="inner", on="author")
        self.authors_data.drop(columns=["name_size", "sha"])
        # Also update the global dataframe
        self.commit_data = self.commit_data.merge(
            self.authors_data[["author", "unique_author"]], how="inner", on="author"
        )
        self.commit_data.index = self.commit_data["datetime"]  # DO NOT REMOVE
        self.update_cache()  # To avoid this very expensive computation in future!
        return self.authors_data

    def set_year(self, y):
        self.year = y

    def select_month_range(self, m1, m2):
        self.month_tup = (m1, m2)

    def select_year_range(self, y1, y2):
        if y1 < y2:
            self.year_tup = (y1, y2)
        else:
            raise Exception("year y1 should be less than year y2")

    def set_month(self, m):
        self.month = m

    def reset_month(self):
        self.month = None

    def reset_year(self):
        self.year = None

    def reset(self, y=None, mo=None):
        self.year = y
        self.month = mo

    def get_monthly_totals_yr(self, df, locc_metric, year=None):
        if year:
            df1 = df[(df["year"] == year)]
        else:
            df1 = df
        # df1 = df1.resample('M').sum()
        df1 = df1.groupby(["month"])
        # For each group, calculate the average of only the metric column
        df1 = df1.aggregate({locc_metric: np.sum})  # monthly averages

        if year is None:
            num_years = df.groupby(["year"]).count()[locc_metric].shape[0]
            df1 = df1 / num_years
        df1["Month"] = df1.index
        return df1

    def get_time_range_df(self, time_range=None, sum=True):
        checkin = pd.DataFrame()
        if time_range == "year":
            checkin_data = self.commit_data[self.commit_data["year"] == self.year]
            if sum:
                checkin = checkin_data.groupby(pd.Grouper(freq="M")).sum()
        if time_range == "month":
            checkin_data = self.commit_data[
                (self.commit_data["month"] == self.month)
                & (self.commit_data["year"] == self.year)
            ]
            if sum:
                checkin = checkin_data.groupby(pd.Grouper(freq="D")).sum()
        if time_range == "year-year":
            checkin_data = self.commit_data[
                (self.commit_data["year"] >= self.year_tup[0])
                & (self.commit_data["year"] <= self.year_tup[1])
            ]
            if sum:
                checkin = checkin_data.groupby(pd.Grouper(freq="M")).sum()
        if time_range == "month-month":
            if self.year_tup is None:
                checkin_data = self.commit_data[
                    (
                        (self.commit_data["month"] >= self.month_tup[0])
                        & (self.commit_data["year"] == self.year)
                    )
                    & (
                        (self.commit_data["month"] == self.month_tup[1])
                        & (self.commit_data["year"] <= self.year)
                    )
                ]
                if sum:
                    checkin = checkin_data.groupby(pd.Grouper(freq="M")).sum()
            else:
                checkin_data = self.commit_data[
                    (
                        (self.commit_data["year"] >= self.year_tup[0])
                        & (self.commit_data["month"] >= self.month_tup[0])
                    )
                    & (
                        (self.commit_data["year"] <= self.year_tup[1])
                        & (self.commit_data["month"] <= self.month_tup[1])
                    )
                ]
                if sum:
                    checkin = checkin_data.groupby(pd.Grouper(freq="M")).sum()

        if time_range is None:
            checkin_data = self.commit_data
            if sum:
                checkin = self.commit_data.groupby(pd.Grouper(freq="M")).sum()

        if not checkin.empty:
            stats_df = checkin.describe().loc[["count", "mean", "std", "min", "max"]]
            return checkin, stats_df  # aggregated
        else:
            stats_df = checkin_data.describe().loc[
                ["count", "mean", "std", "min", "max"]
            ]
            return checkin_data, stats_df  # not aggregated

    def get_dow_averages(self, time_range=None):
        df = self.get_time_range_df(time_range, sum=False)
        return df.groupby(df["dow"]).mean()

    def get_dow_totals(self, time_range=None):
        df = self.get_time_range_df(time_range, sum=False)
        return df.groupby(df["dow"]).sum()

    def get_monthly_averages(self, time_range=None):
        df = self.get_time_range_df(time_range, sum=False)
        return df.groupby(df["month"]).mean()

    def get_monthly_totals(self, time_range=None):
        df = self.get_time_range_df(time_range, sum=False)
        return df.groupby(df["month"]).sum()

    def make_file_developer_df(
        self,
        top_N=-1,
        locc_metric="change-size-cos",
        time_range=None,
        my_df=pd.DataFrame(),
    ):

        print("INFO: Creating developer matrix...")

        # Create the files x developers matrix, using the value_column parameter as the values
        if (
            "unique_author" not in self.commit_data.columns
        ):  # self.authors_data = df.merge(df2, how='inner', on='author')
            self.set_unique_authors()

        if my_df.empty:
            work_df, stats = self.get_time_range_df(time_range, sum=False)
        else:
            # TODO -- enable time ranges with user-provided dataframe my_df
            if locc_metric not in my_df.columns:
                err(
                    "The dataframe you provided to make_file_developer_df() does "
                    'not contain the required "%s" column"' % locc_metric
                )
            work_df = my_df

        if locc_metric not in work_df.select_dtypes(include=["float64", "int"]):
            err(
                "plot_top_N_heatmap column parameter must be one of %s"
                % ",".join(work_df.select_dtypes(include=["float64", "int"]).columns)
            )

        d = pd.DataFrame(
            work_df.groupby(["filepath", "unique_author"])[locc_metric].sum()
        )
        d.reset_index(level=d.index.names, inplace=True)
        # d = d[d[locc_metric] != 0]

        # Compute the stats
        stats_df = d.describe().loc[["count", "mean", "std", "min", "max"]]

        heat_obj = d.pivot_table(
            index="filepath",
            columns="unique_author",
            values=locc_metric,
            aggfunc=np.sum,
            fill_value=0,
        ).dropna()

        # Get a df containing developers (1st column) and total contributions (2nd column)
        sorted_developers = heat_obj.sum(axis="rows").sort_values(ascending=False)
        self.top_developers = sorted_developers
        if top_N > 0:
            top_developers = sorted_developers.head(top_N)
        else:
            top_developers = sorted_developers
        hot_developers = heat_obj[top_developers.index]  # top-N developers

        # Similarly, get a list of top-N files, file path (column 1), changes (column 2)

        top_files = heat_obj.sum(axis="columns").sort_values(ascending=False)
        if top_N > 0:
            top_files = top_files.head(top_N)

        # Now, go back to the original matrix df and extract only the hot files
        hot_files = heat_obj.iloc[heat_obj.index.isin(top_files.to_dict().keys())]
        # drop 0 columns
        hot_files = hot_files.loc[:, (hot_files != 0).any(axis=0)]

        # Next, we need to clean up our top-developer list since some developers got
        # removed in the previous step
        sorted_full_dev_list = list(sorted_developers.to_dict().keys())
        sorted_dev_list = []
        for dev in sorted_full_dev_list:
            if dev in hot_files.columns:
                sorted_dev_list.append(dev)

        # Create a new matrix that has only the top-n developer columns (sorted in
        # descending order); this produces an n x n matrix dataframe, a subset of heat_obj
        if top_N > 0:
            sorted_hot_files = hot_files[sorted_dev_list[:top_N]]
        else:
            sorted_hot_files = hot_files[sorted_dev_list]
        self.top_N_map = sorted_hot_files
        return sorted_hot_files, stats_df

    def extract_directories(self):
        """Extracting names of all the subdirectories in the src directory"""
        print("INFO: Extracting head directories from filepaths...")
        extracted_col = self.commit_data["filepath"]
        df = pd.DataFrame(extracted_col)
        filepaths = df["filepath"].tolist()
        
        # extracting the names of head directory from each filepath e.g. directories in src/ for the petsc project 
        # include vec, mat, ksp, etc
        for i in range(len(filepaths)):
            temp = filepaths[i]
            if(filepaths[i].find('src/') != -1):
                split = temp.split("src/", 1)
                temp = split[1]
                if(temp.find('/') != -1):
                    split = temp.split("/", 1)
                    temp = split[0]
                filepaths[i] = temp
            elif(filepaths[i].find('/') != -1):
                split = temp.split("/", 1)
                temp = split[0]
            filepaths[i] = temp

        # copying the directory names back to the extracted_col df
        df["directory"] = filepaths
        # updating global dataframe
        self.commit_data["directory"] = df["directory"]

    def make_directory_developer_df(self, top_N=-1, locc_metric='change-size-cos', time_range=None, my_df=pd.DataFrame()):
        """
        Create the directories x developers matrix and return the 
        sorted list of directories based on authors' 'knowledge'/concept
        """
        print("INFO: Creating developer matrix...")

        # Create the directory x developers matrix, using the value_column parameter as the values
        if 'unique_author' not in self.commit_data.columns:
            self.set_unique_authors()

        if 'directory' not in self.commit_data.columns:
            self.extract_directories()
        
        if my_df.empty:
            work_df, stats = self.get_time_range_df(time_range, sum=False)
        else:
            # TODO -- enable time ranges with user-provided dataframe my_df
            if locc_metric not in my_df.columns:
                err('The dataframe you provided to make_file_developer_df() does '
                    'not contain the required "%s" column"' % locc_metric)
            work_df = my_df

        if locc_metric not in work_df.select_dtypes(include=['float64', 'int']):
            err('plot_top_N_heatmap column parameter must be one of %s' % ','.join(work_df.select_dtypes(
                include=['float64','int']).columns))

        d = pd.DataFrame(work_df.groupby(['directory', 'unique_author'])[locc_metric].sum())
        d.reset_index(level=d.index.names, inplace=True)

        # Compute the stats
        stats_df = d.describe().loc[['count','mean', 'std', 'min', 'max']]

        heat_obj = d.pivot_table(index='directory', columns='unique_author', values=locc_metric, aggfunc=np.sum,
                                 fill_value=0).dropna()

        # Get a df containing developers (1st column) and total contributions (2nd column)
        sorted_developers = heat_obj.sum(axis='rows').sort_values(ascending=False)
        self.top_developers = sorted_developers
        if top_N> 0: top_developers = sorted_developers.head(top_N)
        else: top_developers = sorted_developers
        hot_developers = heat_obj[top_developers.index]  # top-N developers

        # Similarly, get a list of top-N files, directory (column 1), changes (column 2)
        top_directories = heat_obj.sum(axis='columns').sort_values(ascending=False)
        if top_N > 0: top_directories = top_directories.head(top_N)

        # Now, go back to the original matrix df and extract only the hot files
        hot_directories = heat_obj.iloc[heat_obj.index.isin(top_directories.to_dict().keys())]
        # drop 0 columns
        hot_directories = hot_directories.loc[:, (hot_directories != 0).any(axis=0)]

        # Next, we need to clean up our top-developer list since some developers got
        # removed in the previous step
        sorted_full_dev_list = list(sorted_developers.to_dict().keys())
        sorted_dev_list = []
        for dev in sorted_full_dev_list:
            if dev in hot_directories.columns:
                sorted_dev_list.append(dev)

        # Create a new matrix that has only the top-n developer columns (sorted in
        # descending order); this produces an n x n matrix dataframe, a subset of heat_obj
        if top_N > 0: sorted_hot_directories = hot_directories[sorted_dev_list[:top_N]]
        else: sorted_hot_directories = hot_directories[sorted_dev_list]
        self.top_N_map = sorted_hot_directories

        return sorted_hot_directories, stats_df

    def get_busfactor_data(self, locc_metric='change-size-cos', metric='mul-changes-equal', time_range=None, my_df=pd.DataFrame(), directory_path="", branches=[]):
        """Calculates bus factor based on the four CST algorithm metrics based and the locc_metric 
        provided by the user either on the complete project or on a specific directory"""
        print("INFO: Creating developer matrix...")

        # Create the files x developers matrix, using the value_column parameter as the values
        if 'unique_author' not in self.commit_data.columns:
            self.set_unique_authors()

        if my_df.empty:
            work_df, stats = self.get_time_range_df(time_range, sum=False)
        else:
            if locc_metric not in my_df.columns:
                err('The dataframe you provided to make_file_developer_df() does '
                    'not contain the required "%s" column"' % locc_metric)
            work_df = my_df

        if locc_metric not in work_df.select_dtypes(include=['float64', 'int']):
            err('get_busfactor_data column parameter must be one of %s' % ','.join(work_df.select_dtypes(
                include=['float64','int']).columns))

        prim_devs = []
        secon_devs = []
        primary_dev = sec_devs = 0
        tot_developers = 0

        # picks commits from the branch(es) provided by user, else picks commits from default branch only
        branch_df = pd.DataFrame()
        if len(branches) == 0:
            for b in Patterns.default_branches:
                if len(work_df[work_df['branch'].str.contains(b)]) != 0:
                    branches.append(b)
                    break
        else:
            for i in range(len(branches)):
                if branches[i][0] != "/":
                    branches[i] = "/" + branches[i]
        for i in range(len(branches)):
            branch_df = pd.concat([branch_df, work_df[work_df['branch'].str.contains(branches[i])]], axis=0)
            work_df = work_df[~work_df.branch.str.contains(branches[i])]
        
        work_df = branch_df

        if(not len(work_df)):
            err('The given branch(es) do(es) not exist')
            return 0, pd.DataFrame(), pd.DataFrame(), 0, pd.DataFrame()

        directory_df = pd.DataFrame()
        if len(directory_path):
            directory_df = work_df[work_df['filepath'].str.contains(directory_path)]
            if(not len(directory_df)):
                err('The given directory does not exist')
                return 0, pd.DataFrame(), pd.DataFrame(), 0, pd.DataFrame()
            #sums the value of locc_metric against each author on a certain file in directory_df
            d = pd.DataFrame(directory_df.groupby(['filepath', 'unique_author'])[locc_metric].sum())
            d["dev_knowledge"] = 0
        else:
            d = pd.DataFrame(work_df.groupby(['filepath', 'unique_author'])[locc_metric].sum())
            d["dev_knowledge"] = 0
        d.reset_index(inplace=True)

        #sums total commits by each author regardless of the files
        authors_commits_df = pd.DataFrame(d.groupby(['unique_author'])[locc_metric].sum())
        authors_commits_df.reset_index(inplace=True)

        tot_developers = len(authors_commits_df.index)
        primary_X = 0
        secondary_X = 0
        if tot_developers != 0:
            primary_X = 1/tot_developers
            secondary_X = primary_X/2

        results = authors_commits_df

        # more knowledge is assigned to the developers that modified the file most times
        if(metric == 'mul-changes-equal'):
            tot_commits_per_file = pd.DataFrame(d.groupby(['filepath'])[locc_metric].sum())
            tot_commits_per_file.reset_index(inplace=True)

            # calculating developer knowledge on each file
            for ind in d.index:
                path = d['filepath'][ind]
                author = d['unique_author'][ind]
                d_commits = d[locc_metric][ind]
                index = ((tot_commits_per_file[tot_commits_per_file['filepath']==path].index.values).tolist())[0]
                tot_commits = tot_commits_per_file[locc_metric][index]
                d.iat[ind, d.columns.get_loc('dev_knowledge')] = d_commits/tot_commits

            tot_files = len(tot_commits_per_file.index) #scaling factor
            # aggregating the knowledge on each file to project/directory level
            temp_df = d.drop(columns=['filepath', locc_metric])
            aggregated_df = pd.DataFrame(temp_df.groupby(['unique_author'])['dev_knowledge'].sum())
            aggregated_df['dev_knowledge'] = aggregated_df['dev_knowledge']/tot_files #scaling down by dividing with the total number of files to keep percentage value within 100
            aggregated_df.reset_index(inplace=True)
            aggregated_df.sort_values(by=['dev_knowledge'], ascending=False, inplace=True)

            results = aggregated_df

        # assigns all knowledge of a file to the last developer that modified that file
        elif(metric == 'last-change-all'):
            #for specific directory given by user
            if len(directory_path):
                d = directory_df[['filepath', 'unique_author']].copy()
            #for whole project
            else:
                d = work_df[['filepath', 'unique_author']].copy()
            d.sort_values(by=['filepath'], inplace=True)
            d.reset_index(inplace=True)

            column_names = ["filepath", "unique_author", "datetime", "dev_knowledge"]
            dev_knowledge_df = pd.DataFrame(columns = column_names)

            path = d['filepath'][0]
            datetime = d['datetime'][0]
            author = d['unique_author'][0]
            for ind in range(1,len(d.index)):
                if(path != d['filepath'][ind]):
                    dev_knowledge_df.loc[len(dev_knowledge_df.index)] = [path, author, datetime, 1]
                    path = d['filepath'][ind]
                    datetime = d['datetime'][ind]
                    author = d['unique_author'][ind]
                    ind+=1
                elif datetime < d['datetime'][ind]:
                    path = d['filepath'][ind]
                    datetime = d['datetime'][ind]
                    author = d['unique_author'][ind]

            norm_factor = len(dev_knowledge_df) # total number of files in the directory, branch or project
            d = pd.DataFrame(dev_knowledge_df.groupby(['unique_author'])['dev_knowledge'].sum())
            d["dev_knowledge"] = d["dev_knowledge"].apply(lambda a: a / norm_factor)
            d.sort_values(by=['dev_knowledge'], ascending=False, inplace=True)
            d.reset_index(inplace=True)
            results = d

        else:
            if len(directory_path):
                d = directory_df[['filepath', 'unique_author', locc_metric]].copy()
            else:
                d = work_df[['filepath', 'unique_author', locc_metric]].copy()
            d.sort_values(by=['filepath', 'datetime'], inplace=True)
            d.reset_index(inplace=True)

            # assesses the developer’s knowledge according to the number of non-consecutive changes on the file
            if(metric == 'non-consec-changes'):
                #eliminating consective commits and keeping the one with max locc_metric value
                for ind in range(len(d.index) - 1):
                    path = d['filepath'][ind]
                    author = d['unique_author'][ind]
                    locc_val = d[locc_metric][ind]
                    next_index = ind + 1
                    if(path == d['filepath'][next_index] and author == d['unique_author'][next_index]):
                        if locc_val >= d[locc_metric][next_index]:
                            d.iat[next_index, d.columns.get_loc(locc_metric)] = locc_val
                            d.iat[ind, d.columns.get_loc(locc_metric)] = 0
                        else:
                            d.iat[ind, d.columns.get_loc(locc_metric)] = 0

            # takes into account the position of the modifications in the timeline evolution of the file. 
            # It is used to assign incremental importance to the later modifications on the file.
            elif(metric == 'weighted-non-consec'):
                #multiplying by weight to locc_metric for a file depending upon order
                weight = 1
                for ind in range(len(d.index) - 1):
                    path = d['filepath'][ind]
                    locc_val = d[locc_metric][ind]
                    d.iat[ind, d.columns.get_loc(locc_metric)] = locc_val*weight
                    next_index = ind + 1
                    if(path == d['filepath'][next_index]):
                        weight += 1
                    else:
                        weight = 1

            #total commits of each author on each filepath
            df = pd.DataFrame(d.groupby(['filepath', 'unique_author'])[locc_metric].sum())
            df["dev_knowledge"] = 0
            df.reset_index(inplace=True)

            #total commits on the file by all authors collectively
            tot_commits_per_file = pd.DataFrame(df.groupby(['filepath'])[locc_metric].sum())
            tot_commits_per_file.reset_index(inplace=True)
            tot_commits_per_file.set_index('filepath', inplace=True)

            #calculating developer knowledge of each developer for each file
            it = 0
            for ind in df.index:
                path = df['filepath'][ind]
                author = df['unique_author'][ind]
                d_commits = df[locc_metric][ind]
                tot_commits = tot_commits_per_file[locc_metric][path]
                df.iat[ind, df.columns.get_loc('dev_knowledge')] = d_commits/tot_commits

            #knowledge of each developer on the whole project
            project_knowledge = pd.DataFrame(d.groupby(['unique_author'])[locc_metric].sum())
            project_knowledge.reset_index(inplace=True)
            project_knowledge["dev_knowledge"] = 0
            tot_commits = project_knowledge[locc_metric].sum()

            for ind in project_knowledge.index:
                d_commits = project_knowledge[locc_metric][ind]
                project_knowledge.iat[ind, project_knowledge.columns.get_loc('dev_knowledge')] = d_commits/tot_commits
            
            project_knowledge.sort_values(by=['dev_knowledge'], ascending=False, inplace=True)
            del project_knowledge[locc_metric]
            results = project_knowledge

        for ind in results.index:
            dev_knowledge = results['dev_knowledge'][ind]
            if dev_knowledge >= primary_X:
                primary_dev += 1
                prim_devs.append(results['unique_author'][ind])
            elif dev_knowledge<primary_X and dev_knowledge>=secondary_X:
                sec_devs += 1
                secon_devs.append(results['unique_author'][ind])

        bus_factor = primary_dev + sec_devs

        return tot_developers, prim_devs, secon_devs, bus_factor, results
