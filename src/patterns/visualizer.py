import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np
import pandas as pd
import seaborn as sns
import os

sns.set(font_scale=1.5)
from patterns.patterns import Patterns
from gitutils.utils import *


class Visualizer(Patterns):
    def __init__(self, project_name):
        super().__init__(project_name)
        self.dimensions = None
        self.months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August'
            , 'September', 'October', 'November', 'December']
        self.commit_data = None
        self.yearly_commits = None
        self.monthly_commits = None
        self.max_label_len = 1000
        # Change font size globally
        plt.rcParams['font.size'] = '16'

    def get_data(self, db=None, cache=True):
        self.fetch(db, cache)  # loads up the self.commit_data
        self.close_session()
        self.commit_data.index = self.commit_data['datetime']
        self.commit_data = self.commit_data.drop(columns=['index', 'datetime'])
        self.annotate_metrics()
        self.yearly_commits = self.commit_data.groupby('year').mean()    # this by default includes change-size-cos
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

    def plot_up_down_cols(self, df, up_col, down_col, diff_col=None, log=False, figsize=(16, 12)):
        # Construct a meaningful plot title:
        title = self.project_name.capitalize() + ': Additions vs Deletions'
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
        fig, ax1 = plt.subplots(figsize=figsize)
        sns.barplot(data=d, x='date', y=up_col, alpha=0.5, ax=ax1, palette='crest', hatch='+', label=up_col)
        sns.barplot(data=d, x='date', y=down_col, alpha=0.5, ax=ax1, palette='dark:salmon', hatch='-', label=down_col)
        sns.barplot(data=d, x='date', y=diff_col, ax=ax1, palette='crest', hatch='o', label=diff_col)
        fig.legend(loc='upper left', bbox_to_anchor=(0.05, 0.88), ncol=3)
        ax1.set_title(title)
        if len(ax1.get_xticklabels()) > 30:
            count = 0
            for label in ax1.get_xticklabels():
                if count % 4 == 0: label.set_visible(True)
                else: label.set_visible(False)
                count += 1
            plt.xticks(rotation = 45)
            #ax1.tick_params(labelsize=12)
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Changes')
        fig.autofmt_xdate()
        fig.show()

    def plot_overall_project_locc(self, time_range='year', log=False):
        figsize = (16, 12)
        if time_range == 'year':
            checkin_data = self.commit_data[self.commit_data['year'] == self.year]
            checkin = checkin_data.groupby(pd.Grouper(freq='M')).sum()
        elif time_range == 'month':
            checkin_data = self.commit_data[(self.commit_data['month'] == self.month)
                                            & (self.commit_data['year'] == self.year)]
            checkin = checkin_data.groupby(pd.Grouper(freq='D')).sum()
        else:
            checkin = self.commit_data.groupby(pd.Grouper(freq='Q')).sum()
            figsize = (20, 12)

        self.plot_up_down_cols(df=checkin, up_col='locc+', down_col='locc-',
                               diff_col='change-size-%s' % self.diff_alg, log=log, figsize=figsize)
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
        fig, ax1 = plt.subplots(figsize=(12,6))
        self.reset(y=year1)
        self.monthly_commits.plot(x='month', )
        self.reset(y=year2)
        self.plot_overall_project_locc(axis=ax2)
        handles, labels = ax1.get_legend_handles_labels()
        fig.legend(handles, labels, loc="center left")
        fig.set_visible(True)

    def plot_total_locc_avg(self):
        #self.yearly_commits['locc+ - locc-'] = self.yearly_commits['locc+'] - self.yearly_commits['locc-']
        fig, ax1 = plt.subplots(figsize=(12,6))
        self.yearly_commits.plot(y='locc', linewidth=3, color='r', style='--', ax=ax1)
        self.yearly_commits.plot(y='change-size-cos', linewidth=3, color='b', ax=ax1)
        plt.xticks(fontsize=14)
        plt.yticks(fontsize=14)
        plt.title('The annual average lines of code changed', fontsize=20)
        plt.xlabel('Year', fontsize=16)
        plt.ylabel('Total LOCC', fontsize=16)
        fig.legend(loc='upper left', bbox_to_anchor=(0.05, 0.88), ncol=3)


    def plot_total_locc_moving_avgs(self):
        # colors for the line plot
        colors = ['green', 'red', 'purple', 'blue']
        column = 'locc'
        # the simple moving average over a period of 3 years
        self.yearly_commits['SMA_3'] = self.yearly_commits[column].rolling(3, min_periods=1).mean()

        # the simple moving average over a period of 5 year
        self.yearly_commits['SMA_5'] = self.yearly_commits[column].rolling(5, min_periods=1).mean()

        # the simple moving average over a period of 10 year
        self.yearly_commits['SMA_10'] = self.yearly_commits[column].rolling(10, min_periods=1).mean()

        # line plot 
        self.yearly_commits.plot(y=['locc', 'SMA_3', 'SMA_5', 'SMA_10'], color=colors, linewidth=3,
                                 figsize=(12, 6))

        # modify ticks size
        plt.xticks(fontsize=14)
        plt.yticks(fontsize=14)
        plt.legend(labels=['Average locc', '3-year SMA', '5-year SMA', '10-year SMA'], fontsize=14)

        # title and labels
        plt.title('The annual average lines of code changed', fontsize=20)
        plt.xlabel('Year', fontsize=16)
        plt.ylabel('Total LOCC', fontsize=16)

    def plot_total_locc_moving_avgs_M(self):
        #self.monthly_commits['total_locc'] = self.monthly_commits['locc+'] - self.monthly_commits['locc-']
        self.monthly_commits = self.monthly_commits.drop(self.monthly_commits.index[0])
        # the simple moving average over a period of 3 years
        self.monthly_commits['SMA_3'] = self.monthly_commits.locc.rolling(3, min_periods=1).mean()

        # the simple moving average over a period of 5 year
        self.monthly_commits['SMA_6'] = self.monthly_commits.locc.rolling(5, min_periods=1).mean()

        # the simple moving average over a period of 10 year
        self.monthly_commits['SMA_12'] = self.monthly_commits.locc.rolling(10, min_periods=1).mean()
        # colors for the line plot
        colors = ['red', 'green', 'purple', 'blue']

        # line plot 
        self.monthly_commits.plot(y=['locc', 'SMA_3', 'SMA_6', 'SMA_12'], color=colors, linewidth=3,
                                  figsize=(12, 6))

        # modify ticks size
        plt.xticks(fontsize=14, rotation='vertical')
        plt.yticks(fontsize=14)
        plt.legend(labels=['Average locc', 'Quarterly SMA', '6-month SMA', '12-month SMA'], fontsize=14)

        # title and labels
        plt.title('The monthly average lines of code changed', fontsize=20)
        plt.xlabel('Date', fontsize=16)
        plt.ylabel('Total LOCC', fontsize=16)

    def plot_project_locc_line(self, locc=True, log=False, diff_alg='cos'):
        topi_pd = self.commit_data
        self.annotate_metrics(diff_alg=diff_alg)
        # topi_pd.index = pd.to_datetime(topi_pd.index)
        topi_pd.index = pd.to_datetime(topi_pd.index, utc=True)
        quarter_checkin_i = topi_pd.groupby(pd.Grouper(freq='M')).sum()

        # Don't really want log scale here
        # quarter_checkin_i['log_locc+'] = np.log10(quarter_checkin_i['locc+'])
        # quarter_checkin_i['log_locc-'] = -np.log10(quarter_checkin_i['locc-'])
        # quarter_checkin_i['locc_log_diff'] = quarter_checkin_i['log_locc+'] + \
        #                                    quarter_checkin_i['log_locc-']
        # quarter_checkin_i['log_locc_diff'] = np.log10(quarter_checkin_i[
        #                                    'locc+']-quarter_checkin_i['locc-'])
        # quarter_checkin_i['log_locc_diff'] = np.log10(quarter_checkin_i[
        #                                    'locc+'] + quarter_checkin_i['locc-'])
        # quarter_checkin_i['log_diff_%s'%diff_alg] = np.log10(quarter_checkin_i['change-size-%s'%diff_alg])

        # print(topi_pd)
        if locc:
            y = 'locc'
            tstr = 'LOCC'
        else:
            y = 'change-size-%s' % diff_alg
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
        fig, ax = plt.subplots(figsize=(12, 8))
        sns.set(font_scale=1.5)
        sns.heatmap(self.developer_file_mat, annot=True, linewidths=.5, cmap='icefire')
        if self.year is None:
            plt.title('Overall developers vs files (' + str(self.project_name) + ')')
        else:
            plt.title(str(self.year) + ' : developers vs files (' + self.project_name +
                      ')')
        plt.show()

    def plot_top_N_heatmap(self, top_N=10, value_column='locc', my_df=None):
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
        fig, ax = plt.subplots(figsize=(top_N + 2, top_N))  # Sample figsize in inches
        sns.set(font_scale=1.5)
        sns.heatmap(sorted_hot_files, annot=True, linewidths=.5, ax=ax, fmt=number_fmt, cmap='icefire',
                    cbar_kws={'label': 'Values: %s' % value_column})
        fig.savefig('figures/%s-top-%d-%s-map.png' % (self.project_name, top_N, value_column), format='png', dpi=150,
                    bbox_inches='tight')
        return sorted_hot_files

    def how_was_2020(self, value_column):
        fig, ax = plt.subplots(figsize=(12,8))

        df1 = self.get_monthly_totals(self.commit_data, 2019)
        df1.plot(x='month_num', y=value_column, color='blue',linewidth=3, linestyle='--', ax=ax, label='2019')

        df2 = self.get_monthly_totals(self.commit_data, 2020)
        df2.plot(x='month_num', y=value_column, color='brown',linewidth=3, linestyle='-', ax=ax, label='2020')

        # Average
        d = self.get_monthly_totals(self.commit_data)
        d.plot(x='month_num', y=value_column, color='green',linewidth=3, linestyle=':', ax=ax, label='Average')

        plt.xticks(fontsize=24)
        plt.yticks(fontsize=24)
        #plt.title('Monthly total changes', fontsize=20)
        plt.xlabel('Month', fontsize=24)
        plt.ylabel('Monthly total code change (%s)'%value_column, fontsize=24)
        legend = ax.legend(fancybox=False, fontsize=24, ncol=3, loc='upper left')
        legend.get_frame().set_facecolor('white')
        legend.set_title(self.project_name.capitalize(), prop = {'size':'x-large'})

        if True:
            from matplotlib.cbook import get_sample_data
            poo_img = plt.imread(get_sample_data(os.path.join(os.path.dirname(os.path.realpath("__file__")),'images', 'poo-mark.png')))
            x = df2.index.to_list()
            y = df2[value_column].to_list()
            ax_width = ax.get_window_extent().width
            fig_width = fig.get_window_extent().width
            fig_height = fig.get_window_extent().height
            poo_size = ax_width/(fig_width*len(x))
            poo_axs = [None for i in range(len(x))]
            for i in range(len(x)):
                loc = ax.transData.transform((x[i], y[i]))
                poo_axs[i] = fig.add_axes([loc[0]/fig_width-poo_size/2, loc[1]/fig_height-poo_size/2,
                                       poo_size, poo_size], anchor='C')
                poo_axs[i].imshow(poo_img)
                poo_axs[i].axis("off")

        fig.show()
        fig.savefig('figures/%s-2020-%s-map.png' % (self.project_name, value_column), format='png',
                    dpi=150, bbox_inches='tight')