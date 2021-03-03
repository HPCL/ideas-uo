import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np
import pandas as pd
import seaborn as sns
import os
from patterns.patterns import Patterns
from gitutils.utils import err

sns.set(font_scale=1.25)
sns.set_style('whitegrid', {'legend.frameon': True})

class Visualizer(Patterns):
    metric_name = {'locc-basic' : 'LOCC (added and removed)',
                   'locc': 'LOCC (edited, added, or removed)',
                   'locc-': 'lines removed',
                   'locc+': 'lines added',
                   }

    def __init__(self, project_name=None, project_url=None, exclude_forks=False, forks_only=False):
        super().__init__(project_name, project_url, exclude_forks, forks_only)
        self.dimensions = None
        self.months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August'
            , 'September', 'October', 'November', 'December']
        self.commit_data = None
        self.yearly_commits = None
        self.monthly_commits = None
        self.max_label_len = 1000
        self.save_figures = True
        self.interactive = True
        self.plot_resolution = 75
        self.hide_names = True
        # Change font size globally
        plt.rcParams['font.size'] = '16'
        self.figsize=(10,6)

    def get_data(self, db=None, cache=True, code_only=True):
        if not self.fetch(db, cache):  # loads up the self.commit_data
            return
        print("INFO: Cleaning up data and computing averages...")
        if code_only: self.remove_noncode()    # This makes it feasible to analyze diff
        self.annotate_metrics()                # Compute locc, locc+, locc-, and change-size-cos code change metrics
        self.update_data()
        print("INFO: Done computing averages. %d commits (code only)" % self.commit_data.shape[0])

    def update_data(self):
        # Compute some averages
        self.yearly_commits = self.commit_data.groupby('year').mean()    # this by default includes change-size-cos
        self.monthly_commits = self.commit_data.groupby(["year", "month"]).mean()

    def set_dimensions(self, height, width):
        self.dimensions = (height, width)

    def set_max_label_length(self, len=1000):
        self.max_label_len = len

    def shorten_string(self, string):
        if len(string) < self.max_label_len: return string
        half = int(self.max_label_len / 2)
        return string[:half] + '...' + string[len(string) - half:]

    def plot_up_down_cols(self, df, up_col, down_col, diff_col='change-size-cos', time_range=None, log=False):
        d = df
        if log:
            d[up_col] = np.log10(df[up_col]).fillna(0)
            d[down_col] = -np.log10(df[down_col]).fillna(0)
            d[diff_col] = np.log10(df[diff_col]).fillna(0)
        else:
            d[down_col] = (-df[down_col]).fillna(0)
        d['date'] = d.index
        d['date'] = d['date'].dt.date

        fig, ax1 = plt.subplots(figsize=self.figsize)
        sns.barplot(data=d, x='date', y=up_col, alpha=0.5, ax=ax1, palette='crest', hatch='+', label=up_col)
        sns.barplot(data=d, x='date', y=down_col, alpha=0.5, ax=ax1, palette='dark:salmon', hatch='-', label=down_col)
        sns.barplot(data=d, x='date', y=diff_col, ax=ax1, palette='crest', hatch='o', label=diff_col)
        fig.legend(loc='upper left', bbox_to_anchor=(0.05, 0.88), ncol=3)

        if not self.hide_names: ax1.set_title(self.project.capitalize())
        if len(ax1.get_xticklabels()) > 20:
            count = 0
            for label in ax1.get_xticklabels():
                if count % 5 == 0: label.set_visible(True)
                else: label.set_visible(False)
                count += 1
            plt.xticks(rotation = 45)
            #ax1.tick_params(labelsize=12)
        ax1.set_xlabel('Date')
        ylabel = 'Changes'
        if log: ylabel += ' (log10 scale)'
        ax1.set_ylabel(ylabel)
        fig.autofmt_xdate()
        if self.interactive: fig.show()
        if self.save_figures:
            fig.savefig('figures/%s-trend-%s-%s.png' % (self.project, diff_col, self.get_time_range_str(
                time_range).replace(', ','_')), format='png', dpi=self.plot_resolution, bbox_inches='tight')

    def plot_overall_project_locc(self, time_range=None, log=False):
        if time_range == 'year':
            checkin_data = self.commit_data[self.commit_data['year'] == self.year]
            checkin = checkin_data.groupby(pd.Grouper(freq='M')).sum()
        elif time_range == 'month':
            checkin_data = self.commit_data[(self.commit_data['month'] == self.month)
                                            & (self.commit_data['year'] == self.year)]
            checkin = checkin_data.groupby(pd.Grouper(freq='D')).sum()
        else:
            checkin = self.commit_data.groupby(pd.Grouper(freq='Q')).sum()
        stats_df = checkin.describe().loc[['count', 'mean', 'std', 'min', 'max']]
        if not checkin.empty:
            diff_col = 'change-size-%s' % self.diff_alg
            print(stats_df[['locc+', 'locc-', diff_col]])
            self.plot_up_down_cols(df=checkin, up_col='locc+', down_col='locc-',
                                   diff_col=diff_col, time_range=time_range, log=log)
        else:
            print("We found no data for this time period!")
        return checkin

    def plot_proj_change_line(self, time_range=None, locc_metric='change-size-cos', log=False):
        checkin, stats_df = self.get_time_range_df(time_range)
        if log: checkin[locc_metric] = np.log10(checkin[locc_metric])

        with sns.axes_style("whitegrid"):
            g = sns.relplot(data=checkin, x="datetime", y=locc_metric, markers=True,
                            linewidth = 3, height=6, aspect=1.5, kind="line")
            g.ax.set_xlabel('Date')
            ylabel = 'Changed lines [%s]' % locc_metric
            if log: ylabel += '(log10 scale)'
            g.ax.set_ylabel(ylabel)
            g.fig.autofmt_xdate()
            g.ax.set_title(self.get_title_str(time_range, stats_df, locc_metric, log))
            if self.interactive: g.fig.show()
            if self.save_figures:
                g.fig.savefig('figures/%s-timeline-%s-%s.png' % (self.project, self.diff_alg,
                                                                 self.get_time_range_str(time_range).replace(', ','_')),
                              format='png', dpi=self.plot_resolution, bbox_inches='tight')
        return checkin

    def plot_proj_change_bubble(self, time_range='year', locc_metric="change-size-cos", log=False):
        checkin, stats_df = self.get_time_range_df(time_range)
        if log:
            checkin['locc'] = np.log10(checkin['locc']).fillna(0)
            checkin[locc_metric] = np.log10(checkin[locc_metric]).fillna(0)
        with sns.axes_style("whitegrid"):
            g = sns.relplot(data=checkin, x="datetime", y="locc", size=locc_metric, hue=locc_metric,
                            sizes=(100, 1000), height=6, aspect=1.5, kind="scatter")
            g.ax.set_xlabel('Date')
            ylabel = 'LOCC'
            if log: ylabel += ' (log10 scale)'
            g.ax.set_ylabel(ylabel)
            g.ax.set_title(self.get_title_str(time_range, stats_df, locc_metric, log))
            g.fig.autofmt_xdate()
            if self.interactive: g.fig.show()
            if self.save_figures:
                g.fig.savefig('figures/%s-bubble-%s-%s.png' % (self.project,
                              self.diff_alg, self.get_time_range_str(time_range).replace(', ','_')),
                              format='png', dpi=self.plot_resolution, bbox_inches='tight')
        return checkin

    def plot_proj_y2y(self, year1, year2):
        fig, ax1 = plt.subplots(figsize=self.figsize)
        self.reset(y=year1)
        self.monthly_commits.plot(x='month', )
        self.reset(y=year2)
        self.plot_overall_project_locc(axis=ax2)
        handles, labels = ax1.get_legend_handles_labels()
        fig.legend(handles, labels, loc="center left")
        fig.autofmt_xdate()
        if self.interactive: fig.set_visible(True)

    def plot_total_avg(self, log=False):
        #self.yearly_commits['locc+ - locc-'] = self.yearly_commits['locc+'] - self.yearly_commits['locc-']
        fig, ax1 = plt.subplots(figsize=self.figsize)
        df = self.commit_data.groupby(pd.Grouper(freq='Q')).sum()
        if log: df = np.log10(df)
        df.plot(y='locc', linewidth=3, color='r', style='--', ax=ax1)
        df.plot(y='change-size-cos', linewidth=3, color='b', ax=ax1)
        plt.xticks(fontsize=16)
        plt.yticks(fontsize=16)
        plt.title('Annual average change (LOCC and cos distance)', fontsize=20)
        plt.xlabel('Year', fontsize=18)
        plt.ylabel('Total LOCC', fontsize=18)
        ax1.legend(loc='upper left', ncol=3)
        fig.autofmt_xdate()


    def plot_total_moving_avgs(self, freq='quarter', locc_metric='change-size-cos'):
        # frequency can be year, month, quarter, day
        # colors for the line plot
        colors = ['forestgreen', 'red', 'purple', 'mediumblue']
        df = self.commit_data.groupby(pd.Grouper(freq=freq[0].upper())).sum()

        # the simple moving average over a period of 3 freq. units
        df['SMA_3'] = df[locc_metric].rolling(3, min_periods=1).mean()

        # the simple moving average over a period of 5 freq. units
        df['SMA_5'] = df[locc_metric].rolling(5, min_periods=1).mean()

        # the simple moving average over a period of 10 freq. units
        df['SMA_10'] = df[locc_metric].rolling(10, min_periods=1).mean()

        # line plot
        fig, ax = plt.subplots(figsize=self.figsize)
        df.plot(y=[locc_metric, 'SMA_3', 'SMA_5', 'SMA_10'], ax=ax, color=colors, linewidth=2,
                style=[':','-.','--','-'], figsize=self.figsize, alpha=0.8)

        # modify ticks size
        plt.xticks(fontsize=16)
        plt.yticks(fontsize=16)
        plt.legend(labels=['Average LOCC', '3-%s SMA' %freq, '5-%s SMA' %freq, '10-%s SMA' % freq],
                   loc='upper left',fontsize=16)

        # title and labels
        plt.title('Annual average code changes (%s)' % locc_metric, fontsize=20)
        plt.xlabel('Year', fontsize=18)
        plt.ylabel('Changes (%s)' % locc_metric, fontsize=18)
        fig.autofmt_xdate()

    def plot_developer_file_map(self):
        fig, ax = plt.subplots(figsize=self.figsize)
        sns.heatmap(self.developer_file_mat, annot=True, linewidths=.5, cmap='icefire')
        if self.hide_names: ax.tick_params(left=True, bottom=False)
        title='Developers vs files'
        if self.year is not None: title = str(self.year) + ': ' + title
        if not self.hide_names: title += '(' + str(self.project) + ')'
        plt.title(title)
        if self.interactive: plt.show()

    def plot_top_N_heatmap(self, top_N=10, locc_metric='change-size-cos', time_range=None, my_df=pd.DataFrame()):
        """
        In this function we take the file x developer matrix dataframe and reorder
        it by sorting developer columns by total contributions and then extracting the
        top N most-touched files for the top N most active developers.
        The my_df argument is assuming you know how to create and pass the files vs developers dataframe
        """

        sorted_hot_files, stats_df = self.make_file_developer_df(top_N=top_N, locc_metric=locc_metric,
                                                                 time_range=time_range, my_df=my_df)
        # Figure out number formatting (this is horribly inefficient, I'm sure there is a better way)
        if (self.commit_data[locc_metric].astype(int) == self.commit_data[locc_metric]).all():
            number_fmt = 'g'
        else:
            number_fmt = '.1f'

        # make a lovely heatmap
        fig, ax = plt.subplots(figsize=(top_N + 2, top_N))  # Sample figsize in inches
        if sorted_hot_files.empty:
            print("We found no data for this time period!")
            return sorted_hot_files
        g = sns.heatmap(sorted_hot_files, annot=True, linewidths=.5, ax=ax, fmt=number_fmt, cmap='icefire',
                        cbar_kws={'label': 'Values: %s' % locc_metric})
        if self.hide_names: g.set(xticklabels=[])
        time_range_str = self.get_time_range_str(time_range)
        plt.title(self.get_title_str(time_range, stats_df, locc_metric, False))
        fig.savefig('figures/%s-top-%d-%s-map-%s.png' % (self.project, top_N, locc_metric,
                    time_range_str.replace(', ','_')), format='png', dpi=self.plot_resolution,
                    bbox_inches='tight')
        return sorted_hot_files

    def get_title_str(self, time_range, stats_df, column, log, prefix=''):
        title = ''
        if prefix: title = prefix
        if not self.hide_names:
            title = self.project.capitalize() + ': ' + title
        title += self.get_time_range_str(time_range)
        if log: title += ' (log10 scale)'
        title += ' ' + self.get_stats_string(stats_df, column)
        return title

    def get_stats_string(self, stats_df, column):
        return '[' + ', '.join(["%s: %g" % (k,v) for k,v in stats_df[column].to_dict().items()]) + ']'

    def get_time_range_str(self, time_range):
        if time_range == "year":
            return str(self.year)
        if time_range == "month":
            return str(self.month) + ', ' + str(self.year)
        if time_range == "year-year":
            return str(self.year_tup)
        if time_range == "month-month":
            s = "%d-%d, " % (self.month_tup[0], self.month_tup[1])
            if self.year_tup:
                s += "%d-%d" % (self.year_tup[0], self.year_tup[1])
            else:
                s +=self.year
        return "Entire project"

    def how_was_2020(self, locc_metric='change-size-cos'):
        fig, ax = plt.subplots(figsize=self.figsize)

        df1 = self.get_monthly_totals(self.commit_data, 2019)
        df1.plot(x='month_num', y=locc_metric, color='blue',linewidth=3, linestyle='--', ax=ax, label='2019')

        df2 = self.get_monthly_totals(self.commit_data, 2020)
        df2.plot(x='month_num', y=locc_metric, color='brown',linewidth=3, linestyle='-', ax=ax, label='2020')

        # Average
        d = self.get_monthly_totals(self.commit_data)
        d.plot(x='month_num', y=locc_metric, color='green',linewidth=3, linestyle=':', ax=ax, label='Average')

        if self.hide_names:
            ax.get_xaxis().set_visible(False)
        plt.xticks(fontsize=16)
        plt.yticks(fontsize=16)
        #plt.title('Monthly total changes', fontsize=20)
        plt.xlabel('Month', fontsize=18)
        plt.ylabel('Monthly total code change (%s)'%locc_metric, fontsize=20)
        legend = ax.legend(fancybox=False, fontsize=18, ncol=3, loc='upper left')
        legend.get_frame().set_facecolor('white')
        if not self.hide_names:
            legend.set_title(self.project.capitalize(), prop = {'size':'x-large'})

        if True:
            from matplotlib.cbook import get_sample_data
            poo_img = plt.imread(get_sample_data(os.path.join(os.path.dirname(os.path.realpath("__file__")),'images', 'poo-mark.png')))
            x = df2.index.to_list()
            y = df2[locc_metric].to_list()
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

        if self.interactive: fig.show()
        fig.savefig('figures/%s-2020-%s.png' % (self.project, locc_metric), format='png',
                    dpi=self.plot_resolution, bbox_inches='tight')