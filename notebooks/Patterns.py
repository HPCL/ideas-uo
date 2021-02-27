import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt 
import seaborn as sb 

class Patterns: 
    def __init__(self, commits_table_path, project_name): 
        # path to the the csv containing commits sorted by their "full_date"
        self.commits_table     = pd.read_csv(commits_table_path).drop(columns=['Unnamed: 0'])  
        # to store store list of dataframes sorted in descending order by who made the most commits 
        self.ranked_by_people  = None 
        # to store list (file_name, count) sorted by count 
        self.ranked_files      = None 
        # 2d-matrix (dataframe) of user and files they've touched 
        self.user_file_mat     = None 
        self.year              = None 
        self.month             = None 
        self.project_name      = project_name

    def set_year(self, y): 
        self.year = y 

    def set_month(self, m): 
        self.month = m 

    def reset_month(self):
        self.month = None 

    def reset_year(self):
        self.year = None 

    def reset(self, y=None, mo=None):
        self.year = y 
        self.month = mo 
        self.set_ranked_by_people()

    def rank_pple_b_commits(self):
        """
        Make list of dataframes (slices of self.commits_table) sorted in descending order by rows
        """
        commits = [] 
        seen    = {} 
        contributors = self.commits_table['person']
        for i in range(len(contributors.index)):
            try: 
                throw_away = seen[contributors[i]] 
                if throw_away == 1: 
                    continue 
            except KeyError: 
                seen[contributors[i]] = 1 
                commits_by_p = None 
                comm_p_ym    = pd.DataFrame({'m_dud' : []}) 
                comm_p_m     = pd.DataFrame({'m_dud' : []})
                if self.year is None: 
                    if not (self.month is None) : 
                        commits_by_p = self.commits_table[self.commits_table['person'] == self.commits_table['person'][i]
                                                          & (self.commits_table['month'] == self.month)]
                    else: 
                        commits_by_p = self.commits_table[self.commits_table['person'] == self.commits_table['person'][i]]

                else: 
                    if not (self.month is None) : 
                        commits_by_p = self.commits_table[(self.commits_table['year'] == self.year) 
                                                      & (self.commits_table['month'] == self.month)
                                                      & (self.commits_table['person'] == self.commits_table['person'][i])] 
                    else: 
                        commits_by_p = self.commits_table[(self.commits_table['year'] == self.year) 
                                                      & (self.commits_table['person'] == self.commits_table['person'][i])] 
                commits.append(commits_by_p)
        commits = list(filter(lambda x: len(x['full_date']) > 0, commits)) # remove empty frames 
        if sorted: 
            commits.sort(key=lambda x: len(x['full_date']), reverse=True)
        return commits 

    def set_ranked_by_people(self): 
        self.ranked_by_people = self.rank_pple_b_commits()

    def rank_files(self): 
        """ sort list of (filename, count) by count""" 
        self.set_ranked_by_people() 
        seen = {} 
        for i in range(len(self.ranked_by_people)): 
            df = self.ranked_by_people[i] 
            file_lists = [eval(l) for l in list(df['files'])] 
            for l_file in file_lists: 
                for f in l_file:
                    try: 
                        seen[f] += 1 
                    except KeyError: 
                        seen[f] = 1 
        seen_sorted = sorted(seen.items(), key=lambda x : x[1], reverse=True) 
        return seen_sorted 

    def set_ranked_files(self): 
        self.ranked_files = self.rank_files() 

    def make_file_user_df(self, dims=None): 
        self.set_ranked_files()
        self.set_ranked_by_people() 
        f_index = {} 
        for i in range(len(self.ranked_files)):
            u = self.ranked_files[i] 
            f_index[u[0]] = i 

        ppl_index = {list(self.ranked_by_people[i]['person'])[0] : i for i in range(len(self.ranked_by_people))}

        mat = [[0 for i in ppl_index] for f in f_index] 

        for i in range(len(self.ranked_by_people)): 
            df = self.ranked_by_people[i] 
            file_lists = [eval(l) for l in list(df['files'])] # should see if way to avoid second traversal 
            for file_l in file_lists: 
                for f in file_l: 
                    if f in f_index:
                        person = list(df['person'])[0] 
                        mat[f_index[f]][ppl_index[person]] += 1 
                        
        if dims is None: 
            index_labels  = list(f_index.keys()) 
            column_labels = list(ppl_index.keys()) 
        else: 
            rows = dims[0] 
            cols = dims[1]
            index_labels  = list(f_index.keys())[:rows]
            column_labels = list(ppl_index.keys())[:cols]
            mat  = [r[:cols] for r in mat[:rows]]
        to_return     = pd.DataFrame.from_records(mat, index=index_labels, columns=column_labels) 
        return to_return 

    def set_developer_file_mat(self, dims=None):
        self.user_file_mat = self.make_file_user_df(dims)


class Visualizer(Patterns): 
    def __init__(self, commits_table_path, project_name): 
        Patterns.__init__(self, commits_table_path, project_name) 
        self.dimensions = None 
        self.months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August'
                       , 'September', 'October', 'November', 'December']

    def set_dimensions(self, height, width):
        self.dimensions = (height, width)

    def extend_patterns(self):
        self.set_developer_file_mat(self.dimensions)

    def refresh(self):
        self.extend_patterns()

    
    def view_user_file_map(self):
        fig, ax = plt.subplots(figsize=(12,8)) 
        sb.heatmap(self.user_file_mat, annot=True, linewidths=.5, cmap='icefire') 
        if self.year is None: 
            plt.title('Overall users vs files (' + str(self.project_name) + ')')
        else: 
            plt.title(str(self.year) + ' : users vs files (' + self.project_name + ')')
        plt.show() 

    def view_user_contributions(self, num_users=3):
        fig, ax = plt.subplots() 
        names = [] 
        for i in range(num_users): 
            pd_i = self.ranked_by_people[i] 
            n    = list(pd_i['person'])[0] 
            names.append(n) 

            pd_i.index = pd.to_datetime(pd_i['full_date']) 
            pd_i.index = pd.to_datetime(pd_i.index, utc=True) 
            quarter_checkin_i = pd_i.groupby(pd.Grouper(freq='Q')).sum() 
            quarter_checkin_i['locc'].plot(figsize=(20,8), grid=True, ax=ax, logy=True) 

        ax.set_title("Contributors quarterly changes (" + self.project_name + ")")
        ax.legend(list(map(lambda x: x + 1, list(range(len(names))))))
        plt.show()


    def plot_user_add_delete(self, user_rank, style='bar'):
        fig, axis = plt.subplots(figsize=(20,8))
        user_pd = self.ranked_by_people[user_rank] 
        user_pd.index = pd.to_datetime(user_pd['full_date'])
        user_pd.index = pd.to_datetime(user_pd.index, utc=True)
        if self.month is None: 
            quarter_checkin_i = user_pd.groupby(pd.Grouper(freq='M')).sum() 
        else: 
            quarter_checkin_i = user_pd.groupby(pd.Grouper(freq='D')).sum() 
        quarter_checkin_i['locc+'] = np.log2(quarter_checkin_i['locc+']).fillna(0)
        quarter_checkin_i['locc-'] = -np.log2(quarter_checkin_i['locc-']).fillna(0)
        if style == 'bar': 
            quarter_checkin_i['locc+'].plot(figsize=(15,8), grid=True, ax=axis, kind='bar', sharey=True, color='r')
            quarter_checkin_i['locc-'].plot(figsize=(15,8), grid=True, ax=axis, kind='bar', style='--', sharey=True, color='b')
            axis.set_title(self.project_name + ' user (' + str(user_rank) +') add vs delete over time')
            handles, labels = axis.get_legend_handles_labels() 
            fig.legend(handles, labels, loc="lower center")
            plt.show()
        if style == 'area': 
            y = quarter_checkin_i['locc+'] + quarter_checkin_i['locc-']
            x = np.arange(len(y))
            fig = plt.figure() 
            fig.set_figwidth(20) 
            fig.set_figheight(8) 
            
            plt.plot(x,y)
            z1 = np.array(y)
            z2 = np.array(0.0 * 12)
            plt.fill_between(x, y, 0,
                            where=(z1 >= z2),
                            alpha=0.30, color='green', interpolate=True, label='Positive')
            plt.fill_between(x, y, 0,
                            where=(z1 < z2),
                            alpha=0.30, color='red', interpolate=True, label='Negative')
            plt.legend()

            plt.xlabel('Month')
            plt.xticks(x, ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'])
            plt.ylabel("Net Difference in Lines of Code Changed")
            plt.title(self.project_name + " Top Contributor Add vs Delete Per Month of " + str(self.year))
            plt.show()

    def plot_overall_prjct(self, time_range='year', axis=None): 
        fig, a = plt.subplots(figsize=(20,8))
        if axis is None: 
            axis = a 
        top0_pd = self.ranked_by_people[0] 
        top0_pd.index = pd.to_datetime(top0_pd['full_date'])
        top0_pd.index = pd.to_datetime(top0_pd.index, utc=True)
        checkin_0     = None 
        if time_range == 'month': 
            checkin_0 = top0_pd.groupby(pd.Grouper(freq='D')).sum()
        if time_range == 'year': 
            checkin_0 = top0_pd.groupby(pd.Grouper(freq='M')).sum()
        checkin_sum =  checkin_0
        for i in range(1, len(self.ranked_by_people)):
            topi_pd = self.ranked_by_people[i] 
            topi_pd.index = pd.to_datetime(topi_pd['full_date'])
            topi_pd.index = pd.to_datetime(topi_pd.index, utc=True)
            checkin_i     = None 
            if time_range == 'month': 
                checkin_i = topi_pd.groupby(pd.Grouper(freq='D')).sum() 
            if time_range == 'year': 
                checkin_i = topi_pd.groupby(pd.Grouper(freq='M')).sum() 
            checkin_sum.combine(other=checkin_i, func=(lambda s1, s2 : s1 + s2), fill_value=0)
        checkin_sum['locc+'] = np.log2(checkin_sum['locc+']).fillna(0)
        checkin_sum['locc-'] = -np.log2(checkin_sum['locc-']).fillna(0)
        ax_ans = checkin_sum['locc+'].plot(figsize=(15,8), grid=True, ax=axis, kind='bar', sharey=True, color='r')
        ax_ans1 = checkin_sum['locc-'].plot(figsize=(15,8), grid=True, ax=ax_ans, kind='bar', style='--', sharey=True, color='b')
        if time_range == 'month': 
            ax_ans1.set_title(self.project_name + ' add vs delete in '+ self.months[self.month - 1] + " of " + str(self.year))
        if time_range == 'year': 
            ax_ans1.set_title(self.project_name + ' add vs delete in '+ str(self.year))
        handles, labels = ax_ans.get_legend_handles_labels() 
        fig.legend(handles, labels, loc="upper right")
        if axis == a: 
            plt.show() 
        else:
            fig.set_visible(not fig.get_visible()) 
            plt.clf() 

    def plot_proj_y2y(self, year1, year2): 
        fig, (ax1, ax2) = plt.subplots(1,2) 
        self.reset(y=year1) 
        self.plot_overall_prjct(axis=ax1) 
        self.reset(y=year2) 
        self.plot_overall_prjct(axis=ax2) 
        handles, labels = ax1.get_legend_handles_labels() 
        fig.legend(handles, labels, loc="upper right")
        fig.set_visible(True)



        


