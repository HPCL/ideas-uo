import matplotlib.pyplot as plt 
import plotly.express as px 
import numpy as np
import pandas as pd
import seaborn as sns
sns.set(font_scale=1.5)
from patterns.patterns import Patterns
from gitutils.utils import *


class Visualizer(Patterns): 
    def __init__(self, project_name, db_pwd):
        super().__init__(project_name, db_pwd)
        self.dimensions = None 
        self.months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August'
                       , 'September', 'October', 'November', 'December']
        self.commit_data = None
        self.yearly_commits = None
        self.monthly_commits = None
        self.db_pwd = db_pwd
        self.max_label_len = 1000
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

    def set_max_label_length(self, len=1000):
        self.max_label_len = len

    def extend_patterns(self):
        self.make_file_developer_df()

    def refresh(self):
        self.extend_patterns()

    def shorten_string(self, string):
        if len(string) < self.max_label_len: return string
        half = int(self.max_label_len / 2)
        return string[:half] + '...' + string[len(string) - half:]

    def plot_up_down_cols(self, df, up_col, down_col, diff_col = None, log=False):
        # Construct a meaningful plot title:
        title = self.project_name.capitalize() + ': additions vs deletions'
        if log: title += ' (log10 scale)'

        d = df
        if log:
            d[up_col] = np.log10(df[up_col]).fillna(0)
            d[down_col] = -np.log10(df[down_col]).fillna(0)
            d[diff_col] = np.log10(df[diff_col]).fillna(0)
        else:
            d[down_col] = (-df[down_col]).fillna(0)
        d['date'] = d.index
        d['date'] = d['date'].dt.date

        sns.set_style('whitegrid', {'legend.frameon': True})
        fig, ax1 = plt.subplots(figsize=(16, 12))
        sns.barplot(data=d, x='date', y=up_col, alpha=0.5, ax=ax1, palette='crest', hatch='+', label=up_col)
        sns.barplot(data=d, x='date', y=down_col, alpha=0.5, ax=ax1, palette='dark:salmon', hatch='-', label=down_col)
        sns.barplot(data=d, x='date', y=diff_col, ax=ax1, palette='crest', hatch='o', label=diff_col)
        fig.legend(loc='upper left',bbox_to_anchor=(0.05, 0.88), ncol=3)
        ax1.set_title(title)
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Changes')
        fig.autofmt_xdate()
        fig.show()

    def plot_overall_project_locc(self, time_range='year', log=False):
        if time_range == 'year':
            checkin_data = self.commit_data[self.commit_data['year'] == self.year]
            checkin = checkin_data.groupby(pd.Grouper(freq='M')).sum()
        elif time_range == 'month':
            checkin_data = self.commit_data[(self.commit_data['month'] == self.month)
                                           & (self.commit_data['year'] == self.year)]
            checkin = checkin_data.groupby(pd.Grouper(freq='D')).sum()
        else:
            checkin = self.commit_data.groupby(pd.Grouper(freq='Q')).sum()

        self.plot_up_down_cols(df=checkin, up_col='locc+', down_col='locc-',
                               diff_col='change-size-%s' % self.diff_alg, log=log)
        return checkin

    def plot_proj_change_size(self, time_range='year'):
        self.annotate_metrics()
        checkin = self.get_time_range_df(time_range)
        with sns.axes_style("whitegrid"):
            g = sns.relplot(data=checkin, x="datetime", y="change-size-%s" % self.diff_alg,
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
        fig.legend(handles, labels, loc="center left")
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

    def plot_project_locc_line(self, locc=True, log=False, diff_alg='cos'):
        topi_pd = self.commit_data
        self.annotate_metrics(diff_alg=diff_alg)
        #topi_pd.index = pd.to_datetime(topi_pd.index)
        topi_pd.index = pd.to_datetime(topi_pd.index, utc=True)
        quarter_checkin_i = topi_pd.groupby(pd.Grouper(freq='M')).sum()

        # Don't really want log scale here
        #quarter_checkin_i['log_locc+'] = np.log10(quarter_checkin_i['locc+'])
        #quarter_checkin_i['log_locc-'] = -np.log10(quarter_checkin_i['locc-'])
        #quarter_checkin_i['locc_log_diff'] = quarter_checkin_i['log_locc+'] + \
        #                                    quarter_checkin_i['log_locc-']
        #quarter_checkin_i['log_locc_diff'] = np.log10(quarter_checkin_i[
        #                                    'locc+']-quarter_checkin_i['locc-'])
        #quarter_checkin_i['log_locc_diff'] = np.log10(quarter_checkin_i[
        #                                    'locc+'] + quarter_checkin_i['locc-'])
        #quarter_checkin_i['log_diff_%s'%diff_alg] = np.log10(quarter_checkin_i['change-size-%s'%diff_alg])

        # print(topi_pd)
        if locc:
            y = 'locc'
            tstr = 'LOCC'
        else:
            y = 'change-size-%s'%diff_alg
            tstr = '%s diff' % diff_alg
        with sns.axes_style("whitegrid"):
            g = sns.relplot(data=quarter_checkin_i, x="datetime", y=y,
                            height=6, aspect=1.5, kind="line")
            g.ax.set_xlabel('Date')
            g.ax.set_ylabel('lines added + lines removed [%s]' % tstr)
            g.fig.autofmt_xdate()
            g.fig.show()
        return quarter_checkin_i

    def view_developer_file_map(self):
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


    def plot_top_N_heatmap(self, top_N = 10, value_column='locc', my_df=None):
        """
        In this function we take the file x developer matrix dataframe and reorder
        it by sorting developer columns by total contributions and then extracting the
        top N most-touched files for the top N most active developers.
        The my_df argument is assuming you know how to create and pass the files vs developers dataframe
        """

        sorted_hot_files = self.make_file_developer_df(top_N=top_N, value_column=value_column, my_df=my_df)
        # Figure out number formatting (this is horribly inefficient, I'm sure there is a better way)
        if (self.commit_data[value_column].astype(int) == self.commit_data[value_column]).all():
            number_fmt = 'g'
        else:
            number_fmt = '.1f'

        # make a lovely heatmap
        fig, ax = plt.subplots(figsize=(top_N+2, top_N))  # Sample figsize in inches
        sns.set(font_scale=1.5)
        sns.heatmap(sorted_hot_files, annot=True, linewidths=.5, ax=ax, fmt=number_fmt, cmap='icefire',
                    cbar_kws={'label': 'Values: %s'%value_column})
        fig.savefig('%s-top-%d-%s-map.png' % (self.project_name,top_N,value_column), format='png', dpi=150,
                    bbox_inches='tight')
        return sorted_hot_files
