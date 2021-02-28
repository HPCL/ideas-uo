import matplotlib.pyplot as plt 
import plotly.express as px 
import numpy as np
import pandas as pd
import seaborn as sns
sns.set(font_scale=1.5)
from patterns.patterns import Patterns


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
 

    # def view_developer_contributions(self, num_developers=3):
    #     fig, ax = plt.subplots()
    #     names = []
    #     for i in range(num_developers):
    #         pd_i = self.ranked_by_people[i]
    #         n = list(pd_i['author'])[0]
    #         names.append(n)
    #
    #         pd_i.index = pd.to_datetime(pd_i['datetime'])
    #         pd_i.index = pd.to_datetime(pd_i.index, utc=True)
    #         quarter_checkin_i = pd_i.groupby(pd.Grouper(freq='Q')).sum()
    #         quarter_checkin_i['locc'].plot(figsize=(20,8), grid=True, ax=ax, logy=True)
    #
    #     ax.set_title("Contributors quarterly changes (" + self.project_name + ")")
    #     ax.legend(list(map(lambda x: x + 1, list(range(len(names))))))
    #     plt.show()


    # def plot_developer_add_delete(self, developer_rank):
    #     fig, axis = plt.subplots(figsize=(20,8))
    #     developer_pd = self.ranked_by_people[developer_rank]
    #     developer_pd.index = pd.to_datetime(developer_pd['datetime'])
    #     developer_pd.index = pd.to_datetime(developer_pd.index, utc=True)
    #     if self.month is None: 
    #         quarter_checkin_i = developer_pd.groupby(pd.Grouper(freq='M')).sum()
    #     else: 
    #         quarter_checkin_i = developer_pd.groupby(pd.Grouper(freq='D')).sum()
    #     quarter_checkin_i['locc+'] = np.log2(quarter_checkin_i['locc+']).fillna(0)
    #     quarter_checkin_i['locc-'] = -np.log2(quarter_checkin_i['locc-']).fillna(0)
    #     quarter_checkin_i['locc+'].plot(figsize=(15,8), grid=True, ax=axis, kind='bar', sharey=True, color='r')
    #     quarter_checkin_i['locc-'].plot(figsize=(15,8), grid=True, ax=axis, kind='bar', style='--', sharey=True, color='b')
    #     axis.set_title(self.project_name + ' developer (' + str(developer_rank) +') add
    #     vs delete over time')
    #     handles, labels = axis.get_legend_handles_labels() 
    #     fig.legend(handles, labels, loc="lower center")
    #     plt.show()

    # def changes_line_plot(self, developer_rank):
    #     topi_pd = self.ranked_by_people[developer_rank]
    #     p       = list(topi_pd['author'])[0] # using zero index for developer with most
    #     commits. Can vary for different devs
    #     topi_pd.index = pd.to_datetime(topi_pd['datetime'])
    #     topi_pd.index = pd.to_datetime(topi_pd.index, utc=True)
    #     quarter_checkin_i = topi_pd.groupby(pd.Grouper(freq='M')).sum() 
    #     quarter_checkin_i['locc+'] = np.log2(quarter_checkin_i['locc+'])
    #     quarter_checkin_i['locc-'] = -np.log2(quarter_checkin_i['locc-'])
    #     y = quarter_checkin_i['locc+'] + quarter_checkin_i['locc-']
    #     x = np.arange(len(y))
    #     fig = plt.figure() 
    #     fig.set_figwidth(20) 
    #     fig.set_figheight(8) 
        
    #     plt.plot(x,y)
    #     z1 = np.array(y)
    #     z2 = np.array(0.0 * 10)
    #     plt.fill_between(x, y, 0,
    #                     where=(z1 >= z2),
    #                     alpha=0.30, color='green', interpolate=True, label='Positive')
    #     plt.fill_between(x, y, 0,
    #                     where=(z1 < z2),
    #                     alpha=0.30, color='red', interpolate=True, label='Negative')
    #     plt.legend()
    #     plt.xlabel('Month')
    #     plt.xticks(x, quarter_checkin_i.index, rotation='vertical')
    #     plt.ylabel("Net Difference in Lines of Code Changed")
    #     plt.title(self.project_name + " Top Contributor Add vs Delete Per Month of " + str(self.year));
    #     plt.show()

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

        checkin['locc+'] = np.log2(checkin['locc+']).fillna(0)
        checkin['locc-'] = -np.log2(checkin['locc-']).fillna(0)
        ax_ans = checkin['locc+'].plot(figsize=(15,8), grid=True, ax=axis, kind='bar', sharey=True, color='r')
        ax_ans1 = checkin['locc-'].plot(figsize=(15,8), grid=True, ax=ax_ans, kind='bar', style='--', sharey=True, color='b') 
        if time_range == 'year': 
            ax_ans1.set_title(self.project_name + ' add vs delete in '+ str(self.year))
        if time_range == 'month': 
            ax_ans1.set_title(self.project_name + ' add vs delete in '+  self.months[self.month] + ' of' + str(self.year)) 
        if time_range == None: 
            ax_ans1.set_title(self.project_name + ' overall add vs delete ')
        handles, labels = ax_ans.get_legend_handles_labels() 
        fig.legend(handles, labels, loc="upper right")
        plt.show() 

    def plot_proj_change_size(self, time_range='year', axis=None): 
        if time_range == 'year': 
            checkin_data = self.commit_data[self.commit_data['year'] == self.year]
            checkin = checkin_data.groupby(pd.Grouper(freq='M')).sum()
        if time_range == 'month': 
            checkin_data = self.commit_data[(self.commit_data['month'] == self.month)
                                           & (self.commit_data['year'] == self.year)]
            checkin      = checkin_data.groupby(pd.Grouper(freq='D')).sum()
        if time_range == 'year-year': 
            checkin_data = self.commit_data[(self.commit_data['year'] == self.year_tup[0]) 
                                           | (self.commit_data['year'] == self.year_tup[1])]
            checkin = checkin_data.groupby(pd.Grouper(freq='M')).sum()
        if time_range == 'month-month': 
            if self.year_tup is None: 
                checkin_data = self.commit_data[((self.commit_data['month'] == self.month_tup[0])
                                            & (self.commit_data['year'] == self.year))
                                            | ((self.commit_data['month'] == self.month_tup[1])
                                            & (self.commit_data['year'] == self.year))]
                checkin = checkin_data.groupby(pd.Grouper(freq='M')).sum()
            else: 
                checkin_data = self.commit_data[((self.commit_data['year'] == self.year_tup[0])
                                           & (self.commit_data['month'] == self.month_tup[0]))
                                           | ((self.commit_data['year'] == self.year_tup[1])
                                           & (self.commit_data['month'] == self.month_tup[1]))]
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
        return checkin

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
        quarter_checkin_i['log2_locc+'] = np.log2(quarter_checkin_i['locc+'])
        quarter_checkin_i['log2_locc-'] = -np.log2(quarter_checkin_i['locc-'])
        quarter_checkin_i['locc_log2_diff'] = quarter_checkin_i['locc+'] + \
                                            quarter_checkin_i['locc-']
        quarter_checkin_i['log2_locc_diff'] = np.log2(quarter_checkin_i[
                                                  'locc+']-quarter_checkin_i['locc-'])

        # print(topi_pd)
        with sns.axes_style("whitegrid"):
            g = sns.relplot(data=quarter_checkin_i, x="datetime", y="locc_log2_diff",
                            height=6, aspect=1.5,
                            kind="line")
            g.ax.set_xlabel('Date')
            g.ax.set_ylabel('log2(+lines) - log2(-lines)')
            g.fig.autofmt_xdate()
            g.fig.show()
        return quarter_checkin_i
