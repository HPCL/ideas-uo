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
from gitutils.utils import err

WORD = re.compile(r"\w+")

class Diffutils:
    # See https://github.com/life4/textdistance
    diff_algs = {'cos': td.cosine, 'hamming': td.hamming,
                 'damerau_levenshtein': td.damerau_levenshtein,
                 'jaccard': td.jaccard, 'jaro': td.jaro,
                 'jaro_winkler': td.jaro_winkler, 'bag': td.bag,
                 'editex': td.editex}

    # textdistance.hamming.distance('test', 'text')
    # textdistance.hamming.normalized_distance('test', 'text')

    @staticmethod
    def text_to_vector(text):
        words = WORD.findall(text)
        return Counter(words)


class Patterns(Fetcher):
    path_re = re.compile('^/?(.+/)*(.+)\.(.+)$') # not used yet

    # TODO: create per-project configurations, the opposite of .gitignore
    doc_suffixes = ['rst', 'md', 'txt', 'rtf']
    code_suffixes = ['am', 'awk', 'bash', 'bashrc', 'bat', 'batch',
         'c', 'c#', 'cactus', 'cc', 'ccl', 'cct','charm','cl',
         'cmake', 'cmd', 'code', 'conf', 'cpp', 'csh', 'cshrc',
         'cu', 'cuh', 'def', 'dos', 'el',  'f', 'f77', 'f90', 'f95', 'f03', 'fc', 'ff', 'ffc', 'fh',
         # BN: Not sure about all of these f90 ones (next 3 lines), but leaving, just in case
         'f90-hide', 'f90-orig', 'f90_calhoun', 'f90_eth1', 'f90_eth2_failed',
         'f90_exp', 'f90_future', 'f90_gamma', 'f90_helmholtz', 'f90_hist', 'f90_incaseof', 'f90_new', 'f90_save',
         'f90_sedov', 'f90_temp', 'f90_unused', 'f90_work',
         'ff', 'h', 'h-32', 'h-64', 'hh', 'hpp', 'hxx', 'java', 'ksh', 'lf95', 'm',
         'pbs', 'pl', 'py', 'r', 'script', 'sed', 'sidl',  'src', 'src90', 'th', 'tcl', 'tk', 'yaml', 'yml']

    @staticmethod
    def is_code(path_str):
        if '.' in path_str:
            suffix = path_str.split('.')[-1].lower()
            if suffix in Patterns.code_suffixes:
                return True
        return False

    @staticmethod
    def is_doc(filepath):
        if re.match(r'doc/.*', filepath):
            return True
        elif '.' in filepath:
            suffix = filepath.split('.')[-1].lower()
            if suffix in Patterns.doc_suffixes:
                return True
        return False

    def set_diff_alg(self, diff_alg='cos'):
        if diff_alg not in Diffutils.diff_algs.keys():
            print("Warning: you specified an unknown text distance function, available options are %s (more "
                  "information can be found at https://github.com/life4/textdistance" % str(Diffutils.diff_algs.keys()))
            diff_alg = 'cos'

        self.diff_alg = diff_alg # Diffutils.diff_algs[diff_alg].normalized_distance

    def process_diff(self, diff_str):
        """
        Compute the difference between the original and new code versions in each git diff using the method
        specified as the diff function argument (a function that takes two strings as input and returns a number
        """
        deleted_t = 0
        added_t = 0
        rmvd_code_str = ''
        added_code_str = ''
        diff_str_l = diff_str.splitlines()

        for line in diff_str_l:
            line = line.strip()
            if line == '':
                continue
            if line[0] == '-':
                if len(line) > 1:
                    if line[1] == ' ':
                        deleted_t += 1
                        rmvd_code_str += line[1:].strip()
            if line[0] == '+':
                if len(line) > 1:
                    if len(line) > 2:
                        if line[1] == '+' and line[2] == '+':
                            split_line = line.split(" ")
                            if len(split_line) > 1:
                                commf_name = split_line[1]
                            else:
                                commf_name = ''
                    if line[1] == ' ':
                        added_t += 1
                        added_code_str += line[1:].strip()
        diff_func = Diffutils.diff_algs[self.diff_alg].normalized_distance
        return [added_t + deleted_t, deleted_t, added_t, diff_func(rmvd_code_str, added_code_str)]

    def __init__(self, project_name):
        super().__init__(project_name)
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
        self.project_name = project_name
        self.diff_alg = 'cos'
        self.top_developers = None
        self.top_N_map = None

    def annotate_metrics(self, diff_alg = 'cos'):
        if diff_alg != self.diff_alg: self.set_diff_alg(diff_alg)
        self.commit_data[['locc', 'locc-', 'locc+', 'change-size-%s' % self.diff_alg]] = \
                pd.DataFrame( list(
                    self.commit_data['diff'].map(
                        lambda x: self.process_diff(x)
                    )
                )
                , index=self.commit_data.index
            )

    def sort_data(self):
        self.commit_data.sort_values(by=['datetime', 'sha', 'author']
                                     , ascending=False)

    def remove_docs(self):
        """Remove all documentation-related files (in place mod) """
        self.commit_data = self.commit_data[
            self.commit_data['filepath'].map( lambda x: not Patterns.is_doc(x) )
        ].reindex()

    def remove_noncode(self):
        """Remove all non-cdoe files (in place mod) """
        self.commit_data = self.commit_data[
            self.commit_data['filepath'].map( lambda x: Patterns.is_code(x) )
        ].reindex()

    def set_year(self, y):
        self.year = y

    def select_month_range(self, m1, m2):
        self.month_tup = (m1, m2)

    def select_year_range(self, y1, y2):
        if y1 < y2:
            self.year_tup = (y1, y2)
        else:
            raise Exception('year y1 should be less than year y2')

    def set_month(self, m):
        self.month = m

    def reset_month(self):
        self.month = None

    def reset_year(self):
        self.year = None

    def reset(self, y=None, mo=None):
        self.year = y
        self.month = mo

    def get_monthly_totals(self, df, year=None):
        if year:
            df1 = df[(df['year'] == year)]
        else:
            df1 = df
        df1 = df1.resample('M').sum()
        df1['month_num'] = pd.DatetimeIndex(df1.index).month
        df1 = df1.groupby(['month_num']).mean()
        df1['month_num'] = df1.index
        return df1

    def get_time_range_df(self, time_range='year'):
        if time_range == 'year':
            checkin_data = self.commit_data[self.commit_data['year'] == self.year]
            checkin = checkin_data.groupby(pd.Grouper(freq='M')).sum()
        if time_range == 'month':
            checkin_data = self.commit_data[(self.commit_data['month'] == self.month)
                                           & (self.commit_data['year'] == self.year)]
            checkin      = checkin_data.groupby(pd.Grouper(freq='D')).sum()
        if time_range == 'year-year':
            checkin_data = self.commit_data[(self.commit_data['year'] >= self.year_tup[0])
                                           & (self.commit_data['year'] <= self.year_tup[1])]
            checkin = checkin_data.groupby(pd.Grouper(freq='M')).sum()
        if time_range == 'month-month':
            if self.year_tup is None:
                checkin_data = self.commit_data[((self.commit_data['month'] >= self.month_tup[0])
                                            & (self.commit_data['year'] == self.year))
                                            & ((self.commit_data['month'] == self.month_tup[1])
                                            & (self.commit_data['year'] <= self.year))]
                checkin = checkin_data.groupby(pd.Grouper(freq='M')).sum()
            else:
                checkin_data = self.commit_data[((self.commit_data['year'] >= self.year_tup[0])
                                           & (self.commit_data['month'] >= self.month_tup[0]))
                                           & ((self.commit_data['year'] <= self.year_tup[1])
                                           & (self.commit_data['month'] <= self.month_tup[1]))]
                checkin = checkin_data.groupby(pd.Grouper(freq='M')).sum()

        if time_range == None:
            checkin = self.commit_data.groupby(pd.Grouper(freq='M')).sum()
        return checkin

    def make_file_developer_df(self, top_N=-1, value_column='locc', my_df=None):

        if (my_df is None):
            self.annotate_metrics()

        if my_df is None: work_df = self.commit_data
        else: work_df = my_df

        if value_column not in work_df.select_dtypes(include=['float64','int']):
            err('plot_top_N_heatmap column parameter must be one of %s' % ','.join(work_df.select_dtypes(
                include=['float64','int']).columns))

        #heat_obj = self.make_file_developer_df()
        # Create the files x developers matrix, using the value_column parameter as the values
        d = pd.DataFrame(work_df.groupby(['filepath', 'author'])[value_column].sum())
        d.reset_index(level=d.index.names, inplace=True)
        d = d[d[value_column] != 0]
        d['filepath'] = d['filepath'].transform(self.shorten_string)
        heat_obj = d.pivot_table(index='filepath', columns='author', values=value_column, aggfunc=np.sum,
                                fill_value=0).dropna()

        # Get a df containing developers (1st column) and total contributions (2nd column)
        sorted_developers = heat_obj.sum(axis='rows').sort_values(ascending=False)
        self.top_developers = sorted_developers
        if top_N> 0: top_developers = sorted_developers.head(top_N)
        else: top_developers = sorted_developers
        hot_developers = heat_obj[top_developers.index]  # top-N developers

        # Similarly, get a list of top-N files, file path (column 1), changes (column 2)

        top_files = heat_obj.sum(axis='columns').sort_values(ascending=False)
        if top_N > 0: top_files = top_files.head(top_N)

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
        if top_N > 0: sorted_hot_files = hot_files[sorted_dev_list[:top_N]]
        else: sorted_hot_files = hot_files[sorted_dev_list]
        self.top_N_map = sorted_hot_files
        return sorted_hot_files

    def make_file_developer_df_old(self, dims=None):
        # Not used, see pivot code in visualizer.plot_top_N_heatmap()
        authors = {}
        files = {}
        seen_sha = {}
        seen_author = {}
        seen_files = {}
        author_files = {}
        for i in self.commit_data.index:
            author = self.commit_data['author'][i]
            filename = self.commit_data['filepath'][i]
            sha = self.commit_data['sha'][i]
            try:
                b = seen_sha[sha]
            except KeyError:
                seen_sha[sha] = False
            try:
                a = seen_author[author]
            except KeyError:
                seen_author[author] = False
            try:
                f = seen_files[filename]
            except KeyError:
                seen_files[filename] = False
            try:
                af = author_files[author]
            except KeyError:
                author_files[author] = {}
            try:
                af2 = author_files[author][filename]
            except KeyError:
                author_files[author][filename] = 0
            if not seen_sha[sha]:
                if not seen_author[author]:
                    authors[author] = 1
                    seen_author[author] = True
                else:
                    authors[author] += 1
                if not seen_files[filename]:
                    files[filename] = 1
                    if not seen_author[author]:
                        author_files[author][filename] = 1
                    else:
                        author_files[author][filename] += 1
                    seen_files[filename] = True
                else:
                    files[filename] += 1
                    if not seen_author[author]:
                        author_files[author][filename] = 1
                    else:
                        author_files[author][filename] += 1
                seen_sha[sha] = True
            else:
                if not seen_files[filename]:
                    files[filename] = 1
                    if not seen_author[author]:
                        author_files[author][filename] = 1
                    else:
                        author_files[author][filename] += 1
                else:
                    files[filename] += 1
                    if not seen_author[author]:
                        author_files[author][filename] = 1
                    else:
                        author_files[author][filename] += 1
        # to_ret = pd.DataFrame.from_dict(author_files)
        mat = [[0 for i in authors] for f in files]
        authors_l = list(authors.items())
        authors_l.sort(key=lambda x: x[1], reverse=True)
        files_l = list(files.items())
        files_l.sort(key=lambda x: x[1], reverse=True)
        authors = {a[0]: i for a, i in zip(authors_l, range(len(authors_l)))}
        files = {f[0]: i for f, i in zip(files_l, range(len(files_l)))}
        for aa, fs in author_files.items():
            aa_files = []
            for f, v in fs.items():
                if f in files and (aa in authors):
                    mat[files[f]][authors[aa]] = v
        index_labels = files.keys()
        column_labels = authors.keys()
        if not (dims is None):
            rows = dims[0]
            cols = dims[1]
            index_labels = list(index_labels)[:rows]
            column_labels = list(column_labels)[:cols]
            mat = [r[:cols] for r in mat[:rows]]
        to_ret = pd.DataFrame.from_records(mat, index=index_labels, columns=column_labels)
        to_ret.index.name = 'File'
        self.developer_file_mat = to_ret
        return to_ret
