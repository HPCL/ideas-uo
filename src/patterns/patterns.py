import pandas as pd 
#import numpy as np
import matplotlib.pyplot as plt
#import nltk
import seaborn as sns
sns.set(font_scale=1.5)
import re 
from collections import Counter 
import math 
#from sklearn.feature_extraction.text import TfidfVectorizer
from patterns.fetcher import Fetcher


WORD = re.compile(r"\w+")
def text_to_vector(text):
    words = WORD.findall(text)
    return Counter(words)

def get_cosine(vec1, vec2):
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([vec1[x]**2 for x in vec1.keys()])
    sum2 = sum([vec2[x]**2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    else:
        return float(numerator) / denominator

def is_doc(filepath): 
    pat = r'doc/.*' 
    to_ret = False 
    if re.match(pat, filepath): 
        to_ret = True 
    return to_ret

def diff(text1,text2):
    vector1 = text_to_vector(text1)
    vector2 = text_to_vector(text2)
    cosine = get_cosine(vector1, vector2)
    return cosine

def process_diff(diff_str):  
    deleted_t      = 0
    added_t        = 0 
    rmvd_code_str  = '' 
    added_code_str = ''
    diff_str_l = diff_str.splitlines()
    for line in diff_str_l: 
        line = line.strip()
        if line == '': 
            continue 
        else: 
            if line[0] == '-': 
                if len(line) > 1: 
                    if line[1] == ' ': 
                        deleted_t += 1 
                        rmvd_code_str   += line[1:].strip()  
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
    similarity = diff(rmvd_code_str, added_code_str) 
    return [added_t + deleted_t, deleted_t, added_t, 1-similarity]


class Patterns(Fetcher): 
    def __init__(self, project_name): 
        super().__init__(project_name)
        # self.close_session()
        # to store store list of dataframes sorted in descending order by who made the most commits 
        self.ranked_by_people  = None 
        # to store list (file_name, count) sorted by count 
        self.ranked_files      = None 
        # 2d-matrix (dataframe) of developers and files they've touched
        self.developer_file_mat     = None
        self.year              = None 
        self.month             = None 
        self.year_tup          = None 
        self.month_tup         = None 
        self.project_name      = project_name
        self.top_N_map         = None

    def annotate_metrics(self): 
        self.commit_data[['locc', 'locc-'
                         , 'locc+', 'change-size']] = pd.DataFrame(
                             list(
                                 self.commit_data['diff'].map(
                                     lambda x : process_diff(x)
                                 )
                             )
                             , index=self.commit_data.index 
                         )

    def sort_data(self): 
        self.commit_data.sort_values(by=['datetime', 'sha', 'author']
                             , ascending=False)


    def filter_docs(self): 
        self.commit_data = self.commit_data[
            self.commit_data['filepath'].map(
                lambda x : not is_doc(x)
            )
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

    def make_file_developer_df(self, dims=None):
        authors     = {} 
        files       = {} 
        seen_sha    = {} 
        seen_author = {} 
        seen_files  = {} 
        author_files = {}
        for i in self.commit_data.index: 
            author   = self.commit_data['author'][i] 
            filename = self.commit_data['filepath'][i] 
            sha      = self.commit_data['sha'][i] 
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
        authors = {a[0] : i for a,i in zip(authors_l,range(len(authors_l)))}
        files  = {f[0] : i for f,i in zip(files_l,range(len(files_l)))}
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

    def view_top_N_map(self, n = 10):
        """
        In this function we take the file x developer matrix dataframe and reorder
        it by sorting developer columns by total contributions and then extracting the
        top N most-touched files for the top N most active developers.
        """
        heat_obj = self.make_file_developer_df()

        # Get a df containing developers (1st column) and total contributions (2nd column)
        sorted_developers = heat_obj.sum(axis='rows').sort_values(ascending=False)
        top_developers = sorted_developers.head(n)
        hot_developers = heat_obj[top_developers.index]  # top-N developers

        # Similarly, get a list of top-N files, file path (column 1), changes (column 2)
        top_files = heat_obj.sum(axis='columns').sort_values(ascending=False).head(n)

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
        sorted_hot_files = hot_files[sorted_dev_list[:n]]

        # make a lovely heatmap
        fig, ax = plt.subplots(figsize=(n, n))  # Sample figsize in inches
        sns.set(font_scale=1.5)
        sns.heatmap(sorted_hot_files, annot=True, linewidths=.5, ax=ax, fmt='g')
        fig.savefig('%s-top-%d-map.png' % (self.project_name,n), format='png', dpi=150)
        self.top_N_map = sorted_hot_files
        return sorted_hot_files

    def view_developer_file_map(self):
        fig, ax = plt.subplots(figsize=(12,8))
        sns.set(font_scale=1.5)
        sns.heatmap(self.developer_file_mat, annot=True, linewidths=.5, cmap='icefire')
        if self.year is None: 
            plt.title('Overall developers vs files (' + str(self.project_name) + ')')
        else: 
            plt.title(str(self.year) + ' : developers vs files (' + self.project_name +
                      ')')
        plt.show()






    


    



        


