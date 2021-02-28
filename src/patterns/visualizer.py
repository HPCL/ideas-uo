import matplotlib.pyplot as plt 
import plotly.express as px 
import numpy as np
import pandas as pd
import seaborn as sns
sns.set(font_scale=1.5)
from patterns.patterns import Patterns
from gitutils.utils import *


class Visualizer(Patterns): 
    def __init__(self, project_name: str): 
        super().__init__(project_name)
        self.dimensions = None 
        self.months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August'
                       , 'September', 'October', 'November', 'December']
        self.commit_data = None
        self.yearly_commits = None
        self.monthly_commits = None
        # Change font size globally
        plt.rcParams['font.size'] = '16'

    def get_data(self, db=None):
        self.fetch(db)  # loads up the self.commit_data
        self.close_session()
        self.commit_data.index   = self.commit_data['datetime']
        self.commit_data = self.commit_data.drop(columns=['index', 'datetime'])
        self.annotate_metrics()
        self.yearly_commits = self.commit_data.groupby('year').mean()
        self.monthly_commits = self.commit_data.groupby(["year", "month"]).mean()

    def set_dimensions(self, height, width):
        self.dimensions = (height, width)

    def extend_patterns(self):
        self.set_developer_file_mat(self.dimensions)

    def refresh(self):
        self.extend_patterns()


    def plot_overall_project_locc(self, time_range='year', axis=None):
        fig, a = plt.subplots(figsize=(20,8))
        if axis is None: 
            axis = a
        if time_range == 'year': 
            checkin_data = self.commit_data[self.commit_data['year'] == self.year]
            checkin = checkin_data.groupby(pd.Grouper(freq='M')).sum()
        if time_range == 'month': 
            checkin_data = self.commit_data[(self.commit_data['month'] == self.month)
                                           & (self.commit_data['year'] == self.year)]
            checkin      = checkin_data.groupby(pd.Grouper(freq='D')).sum()
        if time_range == None: 
            checkin = self.commit_data.groupby(pd.Grouper(freq='Q')).sum() 

        if not 'log_loc+' in checkin.columns:
            checkin['log_locc+'] = np.log10(checkin['locc+']).fillna(0)
            checkin['log_locc-'] = -np.log10(checkin['locc-']).fillna(0)
        ax_ans = checkin['log_locc+'].plot(figsize=(15,8), grid=True, ax=axis, kind='bar', sharey=True, color='r')
        ax_ans1 = checkin['log_locc-'].plot(figsize=(15,8), grid=True, ax=ax_ans, kind='bar', style='--', sharey=True,
                                         color='b')
        if time_range == 'year': 
            ax_ans1.set_title(self.project_name + ' add vs delete in '+ str(self.year)
                              + ' (log10 scale)')
        if time_range == 'month': 
            ax_ans1.set_title(self.project_name + ' add vs delete in '+  self.months[
                self.month] + ' of' + str(self.year) + ' (log10 scale)')
        if time_range == None: 
            ax_ans1.set_title(self.project_name + ' overall add vs delete (log10 scale)')
        handles, labels = ax_ans.get_legend_handles_labels() 
        fig.legend(handles, labels, loc="center right")
        ax_ans.set_xlabel('Date')
        ax_ans.set_xticklabels([pandas_datetime.strftime("%Y-%m-%d") for pandas_datetime
                             in checkin['locc+'].index])
        plt.show()
        return checkin

    def plot_proj_change_size(self, time_range='year', axis=None): 
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
        #fig = sns.line(checkin, x=checkin.index, y=checkin['change-size'])
        with sns.axes_style("whitegrid"):
            g = sns.relplot(data=checkin, x="datetime", y="change-size",
                            kind="line", height=6, aspect=1.5)
            g.ax.set_xlabel('Date')
            g.ax.set_ylabel('Total number of changed lines')
            g.fig.autofmt_xdate()
            g.fig.show()
        return checkin, g.ax

    def plot_proj_y2y(self, year1, year2): 
        fig, (ax1, ax2) = plt.subplots(1,2) 
        self.reset(y=year1) 
        self.plot_overall_project_locc(axis=ax1)
        self.reset(y=year2) 
        self.plot_overall_project_locc(axis=ax2)
        handles, labels = ax1.get_legend_handles_labels() 
        fig.legend(handles, labels, loc="upper right")
        fig.set_visible(True)

    def plot_total_locc_avg(self): 
        self.yearly_commits['total_locc'] = self.yearly_commits['locc+']-self.yearly_commits['locc-']
        self.yearly_commits.plot( y='total_locc',linewidth=3, figsize=(12,6))
        plt.xticks(fontsize=14)
        plt.yticks(fontsize=14)
        plt.title('The annual average lines of code changed', fontsize=20)
        plt.xlabel('Year', fontsize=16)
        plt.ylabel('Total locc', fontsize=16)

    def plot_total_locc_moving_avgs(self): 
        # colors for the line plot
        colors = ['green', 'red', 'purple', 'blue']

        # the simple moving average over a period of 3 years
        self.yearly_commits['SMA_3'] = self.yearly_commits.total_locc.rolling(3, min_periods=1).mean()

        # the simple moving average over a period of 5 year
        self.yearly_commits['SMA_5'] = self.yearly_commits.total_locc.rolling(5, min_periods=1).mean()

        # the simple moving average over a period of 10 year
        self.yearly_commits['SMA_10'] = self.yearly_commits.total_locc.rolling(10, min_periods=1).mean()

        # line plot 
        self.yearly_commits.plot(y=['total_locc', 'SMA_3', 'SMA_5', 'SMA_10'], color=colors, linewidth=3, figsize=(12,6))

        # modify ticks size
        plt.xticks(fontsize=14)
        plt.yticks(fontsize=14)
        plt.legend(labels =['Average locc', '3-year SMA', '5-year SMA', '10-year SMA'], fontsize=14)

        # title and labels
        plt.title('The annual average lines of code changed', fontsize=20)
        plt.xlabel('Year', fontsize=16)
        plt.ylabel('Total locc', fontsize=16)

    def plot_total_locc_moving_avgs_M(self): 
        self.monthly_commits['total_locc'] = self.monthly_commits['locc+']-self.monthly_commits['locc-']
        self.monthly_commits= self.monthly_commits.drop(self.monthly_commits.index[0])
        # the simple moving average over a period of 3 years
        self.monthly_commits['SMA_3'] = self.monthly_commits.total_locc.rolling(3, min_periods=1).mean()

        # the simple moving average over a period of 5 year
        self.monthly_commits['SMA_6'] = self.monthly_commits.total_locc.rolling(5, min_periods=1).mean()

        # the simple moving average over a period of 10 year
        self.monthly_commits['SMA_12'] = self.monthly_commits.total_locc.rolling(10, min_periods=1).mean()
        # colors for the line plot
        colors = ['red', 'green', 'purple', 'blue']

        # line plot 
        self.monthly_commits.plot(y=['total_locc', 'SMA_3', 'SMA_6', 'SMA_12'], color=colors, linewidth=3, figsize=(12,6))

        # modify ticks size
        plt.xticks(fontsize=14, rotation='vertical')
        plt.yticks(fontsize=14)
        plt.legend(labels =['Average locc', 'Quarterly SMA', '6-month SMA', '12-month SMA'], fontsize=14)

        # title and labels
        plt.title('The monthly average lines of code changed', fontsize=20)
        plt.xlabel('Date', fontsize=16)
        plt.ylabel('Total locc', fontsize=16)

    def plot_project_locc_line(self): 
        topi_pd = self.commit_data
        topi_pd.index = pd.to_datetime(topi_pd.index)
        topi_pd.index = pd.to_datetime(topi_pd.index, utc=True)
        quarter_checkin_i = topi_pd.groupby(pd.Grouper(freq='M')).sum()
        if not 'log_locc+' in quarter_checkin_i.columns:
            quarter_checkin_i['log_locc+'] = np.log10(quarter_checkin_i['locc+'])
            quarter_checkin_i['log_locc-'] = -np.log10(quarter_checkin_i['locc-'])
            quarter_checkin_i['locc_log_diff'] = quarter_checkin_i['log_locc+'] + \
                                                quarter_checkin_i['log_locc-']
            quarter_checkin_i['log_locc_diff'] = np.log10(quarter_checkin_i[
                                                'locc+']-quarter_checkin_i['locc-'])

        # print(topi_pd)
        with sns.axes_style("whitegrid"):
            g = sns.relplot(data=quarter_checkin_i, x="datetime", y="locc_log_diff",
                            height=6, aspect=1.5,
                            kind="line")
            g.ax.set_xlabel('Date')
            g.ax.set_ylabel('log10(+lines) - log10(-lines)')
            g.fig.autofmt_xdate()
            g.fig.show()
        return quarter_checkin_i

    def view_developer_file_map(self):
        if not 'change-size' in self.commit_data.columns:
            self.annotate_metrics()
        fig, ax = plt.subplots(figsize=(12,8))
        sns.set(font_scale=1.5)
        sns.heatmap(self.developer_file_mat, annot=True, linewidths=.5, cmap='icefire')
        if self.year is None:
            plt.title('Overall developers vs files (' + str(self.project_name) + ')')
        else:
            plt.title(str(self.year) + ' : developers vs files (' + self.project_name +
                      ')')
        plt.show()


    def plot_top_N_heatmap(self, n = 10, column='locc'):
        """
        In this function we take the file x developer matrix dataframe and reorder
        it by sorting developer columns by total contributions and then extracting the
        top N most-touched files for the top N most active developers.
        """
        if not 'change-size' in self.commit_data.columns:
            self.annotate_metrics()

        if column not in ['locc', 'locc-', 'locc+', 'change-size']:
            err('plot_top_N_heatmap column parameter must be one of %s' % ','.join(['locc', 'locc-', 'locc+',
                                                                                    'change-size']))

        #heat_obj = self.make_file_developer_df()
        # Create the files x developers matrix, using the column parameter as the values
        d = pd.DataFrame(self.commit_data.groupby(['filepath', 'author'])[column].sum())
        d.reset_index(level=d.index.names, inplace=True)
        d = d[d[column] != 0]
        heat_obj = d.pivot_table(index='filepath', columns='author', values=column, aggfunc=np.sum,
                                fill_value=0).dropna()

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
        sns.heatmap(sorted_hot_files, annot=True, linewidths=.5, ax=ax, fmt='g', cmap='icefire')
        fig.savefig('%s-top-%d-map.png' % (self.project_name,n), format='png', dpi=150)
        self.top_N_map = sorted_hot_files
        return sorted_hot_files