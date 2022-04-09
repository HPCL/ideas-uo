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
            # We consider lines starting with a single '+' or '-' character
            if len(line) > 2 and line[0] in ["-", "+"] and line[1] == " ":
                summary += line[0]
                if line[0] == "-":
                    old += line
                if line[0] == "+":
                    new += line

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
        print("INFO: Extracting head directories from filepaths...")
        extracted_col = self.commit_data["filepath"]
        df = pd.DataFrame(extracted_col)
        filepaths = df["filepath"].tolist()
        
        # extracting the name of head directory from each filepath
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
        top_files = heat_obj.sum(axis='columns').sort_values(ascending=False)
        if top_N > 0: top_files = top_files.head(top_N)

        sorted_hot_files = pd.DataFrame()
        stats_df = pd.DataFrame()
        return sorted_hot_files, stats_df