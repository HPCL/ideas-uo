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

    # edits_summary_re.findall('--++-+-+--++--++-+--') produces ['--++', '-+', '-+', '--++', '--++', '-+']
    edits_summary_re = re.compile(r'(-+\++)')


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

    def process_single_commit(self, lines_list):
        # First, create a very brief summary of the changes, e.g., for one set of diffs, produce '--++-+-+--++--++-+--'
        #print(lines_list)
        summary, old, new = '', '', ''
        for line in lines_list:
            # We consider lines starting with a single '+' or '-' character
            if len(line) > 2 and line[0] in ['-', '+'] and line[1] == ' ':
                summary += line[0]
                if line[0] == '-': old += line
                if line[1] == '+': new += line

        # Update "change" (vs. adding or removing lines), e.g.,  --++ means that two lines are modified, not that
        # two lines are deleted and then two added (line count 2 vs 4).
        # Example input summary: '++----++-+-+--++--++-+--'
        # Example resulting values for removed, added, edited: 4 2 9
        s = summary
        removed, added, edited = 0, 0, 0
        edits = Patterns.edits_summary_re.findall(summary)
        for edit in edits:
            index = s.find(edit)    # next "edit" candidate
            rm, add = s[:index].count('-'), s[:index].count('+')  # non-edits
            ed_rm, ed_add = edit.count('-'), edit.count('+')
            ed = min(ed_rm, ed_add) # actual size of edit, basically counts of matching -+ strings
            edited += ed
            removed, added = removed + rm + ed_rm - ed, added + add + ed_add - ed
            s = s[index + len(edit):]  # advance
        # trailing changes
        removed, added = removed + s.count('-'), added + s.count('+')

        # Total LOCC that takes into acount "edits"
        locc = removed + added + edited

        # Finally, compute the default distance metric
        diff = Diffutils.diff_algs[self.diff_alg].distance(old, new)
        #print(summary, len(summary), locc, removed, added, diff)
        return [summary, len(summary), locc, removed, added, diff]

    def set_diff_alg(self, diff_alg='cos', compute=True, recompute=False):
        if diff_alg not in Diffutils.diff_algs.keys():
            print("Warning: you specified an unknown text distance function, available options are %s (more "
                  "information can be found at https://github.com/life4/textdistance. Defaulting to cos distance." %
                  str(Diffutils.diff_algs.keys()))
            diff_alg = 'cos'

        self.diff_alg = diff_alg # To apply: Diffutils.diff_algs[diff_alg].distance (str1, str2), also normalized_distance

        # compute the new diff it not already available:
        if not compute: return
        colname = 'change-size-%s' % self.diff_alg
        if colname not in self.commit_data.columns: compute = True
        if compute or recompute:
            self.commit_data[['diff_summary', 'locc-basic', 'locc', 'locc-', 'locc+', colname]] = \
                pd.DataFrame(list(
                    self.commit_data['diff'].str.split(pat="\n").map(lambda x: self.process_single_commit(x))
                    )
                    , index=self.commit_data.index
                )

    def annotate_metrics(self, diff_alg = 'cos'):
        # Add columns with commonly used metrics
        # avoid recomputing the default metrics if they are already there
        if 'locc' not in self.commit_data.columns or 'change-size-%s' % diff_alg not in self.commit_data.columns:
            self.set_diff_alg(diff_alg, compute=True)

    def sort_data(self):
        self.commit_data.sort_values(by=['datetime', 'sha', 'author'], ascending=False)

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
