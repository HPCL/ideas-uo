#!/usr/bin/env python
# coding: utf-8

# # Software development patterns through git data mining
# 

# In[ ]:


import sys, os, getpass, warnings
warnings.filterwarnings('ignore')
from patterns.visualizer import Visualizer


# Create a `Visualizer` object for a project, e.g., for Spack, `vis = Visualizer('spack')`. This brings in data from database and annotate it with *locc*, *locc+*, *locc-*, *change-size-cos* = *1-similarity* (**expensive call**). The data is cached locally after it's fetched from the database and subsequently loaded from disk, unless you specify the `cache=False` parameter, e.g., `vis.get_data(cache=False)`. Available projects include `'lammps', 'spack', 'petsc', 'Nek5000', 'nwchem', 'E3SM', 'qmcpack', 'qdpxx', 'LATTE', 'namd', 'enzo-dev'` (the full list can be obtained with by calling the `Visualizer()` constructor without arguments.
# 
# The `get_data` method automatically removes changes associated with non-code files. The determination of what is code is made by including common suffixes, as well as checking manually a sampling of ECP projects for the suffixes used for things that can be labeled as code (vs. input simulation data, documentation, or generated files), for a list of suffixes, refer to the `Patterns.code_suffixes` list in [patterns.py](https://github.com/HPCL/ideas-uo/blob/master/src/patterns/patterns.py). This makes the analysis of decades of project data feasible. You can disable this if desired, by passing the `code_only=False` parameter to `get_data`. You can also explicitly remove non-code rows with `vis.remove_noncode()`. Optionally, you can remove files that are likely copies of external code (path contains `extern` or `contrib`) with `vis.remove_external()`.

# In[ ]:


vis = Visualizer(project_name='spack')
vis.get_data()


# By default, the names of projects and developers are not shown in the figures. If you wish to include project names, set `vis.hide_names` to `False`.

# In[ ]:


vis.hide_names = False


# Let's start with some global views -- this plot shows the entire project's git history (including imports from other RCS). The three different metrics shown represent different ways of quantifying the magnitude of the change based on the differences produced by `git log`. The `locc+` and `locc-` lines are lines added and removed, respectively. The `change-size-cos` is one of many text difference metrics, which computes the "distance" between the old and new code snippets in each commit. We discuss distance metrics in more detail later.

# In[ ]:


df = vis.plot_overall_project_locc(log=True)


# to focus on a given year and/or month, set *year* and *month* fields

# In[ ]:


vis.set_year(2020)
vis.set_month(10)


# to plot for a given year, provide *time_range='year'*

# In[ ]:


df = vis.plot_overall_project_locc(time_range='year',log=True)


# similarly to plot for a given month, set *time_range='month'*

# In[ ]:


df = vis.plot_overall_project_locc(time_range='month',log=True)


# ### Finding trends with averages
# We can plot the annual averages timeline for the entire project's history (by default showing LOCC and cos distance) with `plot_total_avg`. Several moving average plots are available, with different aggregation granularities (year, month) and different sliding window sizes.

# In[ ]:


vis.plot_total_avg(log=True)


# We can also compute different moving averages, indicating the aggregation frequency with the `freq` paramater. The default is `quarter`.

# In[ ]:


vis.plot_total_moving_avgs(freq='year')


# In[ ]:


vis.plot_total_moving_avgs()


# In[ ]:


vis.plot_total_moving_avgs(freq='month')


# ## More timelines
# This reflects changed lines of code as reported in git commit diffs. We have two functions that generate timeline plots of a change metric: `plot_proj_change_line` and `plot_proj_change_bubble`. By default, they show the entire range of selected dates and use the cos distance metric. You can specify a different metric with the `locc_metric` argument, e.g., `vis.plot_proj_change_line(locc_metric='locc')`

# In[ ]:


df = vis.plot_proj_change_line()


# And looking at both line counts (LOCC) and the distance based `change-size-cos` at the same time. If not specified, the time_range argument defaults None, which indicates the entire time period of the dataset.

# In[ ]:


vis.set_month(11)
df = vis.plot_proj_change_bubble(time_range="month")


# We can choose to zoom into a specific year, recall that previously we did `vis.set_year(2020)`.

# In[ ]:


df = vis.plot_proj_change_bubble(time_range='year')


# Or a specific year range.

# In[ ]:


vis.select_year_range(2019,2020)
vis.plot_proj_change_bubble(time_range='year-year')
df = vis.plot_overall_project_locc(time_range='year-year',log=True)


# We can also zoom into a single month; recall we previously did:
# ```
# vis.set_year(2019)
# vis.set_month(10)
# ```

# In[ ]:


_ = vis.plot_proj_change_line(time_range='month')


# Or a month range

# In[ ]:


vis.select_month_range(5,11)
df = vis.plot_proj_change_line(time_range='month-month')


# ## Using a text distance metric to adjust the size of the changes
# 
# We use the python [textdistance](https://github.com/life4/textdistance) module. The following algorithms have been integrated with the visualizer.
# ```
# 'cos', 'hamming', 'damerau_levenshtein', 'jaccard', 'jaro', 'jaro_winkler', 'bag', 'editex'
# ```
# Any of the above plots can be made with any line counting metric, typically specified through the `locc_metric` argument.

# In[ ]:


vis.set_diff_alg('jaccard')
df = vis.plot_proj_change_line()
_ = vis.plot_proj_change_bubble()


# ## More patterns
# Here we look at a combination of the the high-churn and domain champion patterns. Basically we are focusing on the files that have the most changes and restricting the developers by those with the biggest contributions. One tricky issue that makes this nontrivial is that contributors use different names for their contributions. We have implemented a fuzzy name matching scheme of author names using the python `fuzzywuzzy` package to consolidate single-author contributions as much as possible.

# In[ ]:


N = 10
vis.reset()
#vis.set_unique_authors()  # force author recomputation, this is expensive, so the result will be cached
vis.set_max_ylabel_length(30)
top_N = vis.plot_top_N_heatmap(N, locc_metric='locc')
top_N.head()


# In[ ]:


top_N_cos = vis.plot_top_N_heatmap(N, locc_metric='change-size-cos')
top_N_cos.head()


# In[ ]:


vis.set_year(2020)
top_N_cos = vis.plot_top_N_heatmap(N, time_range='year', locc_metric='change-size-cos')
top_N_cos.head()


# We can also easily see the exact differences between different ways of measuring change. This is not something that we normally compute frequently, hence there isn't a special plot function.

# In[ ]:


file_dev_locc, _ = vis.make_file_developer_df(locc_metric='locc')
file_dev_diff, _ = vis.make_file_developer_df(locc_metric='change-size-cos')


# In[ ]:


diff_df = file_dev_locc.sub(file_dev_diff, axis=0)
print("Total number of developers: %d" % diff_df.shape[1])
df = vis.commit_data
df['locc - cos diff'] = df['locc']-df['change-size-cos']
d = vis.plot_top_N_heatmap(top_N = 10, locc_metric='locc - cos diff', my_df=df)


# We can generate the "hot-files" data for any time period, the way we select it is the same as previously described.

# In[ ]:


N = 10
vis.set_year(2019)
vis.set_month(11)
vis.set_max_ylabel_length(30)
top_N = vis.plot_top_N_heatmap(N, time_range="month",locc_metric='locc')
top_N.head()


# ## In the zone
# Here we look at what days of the week and times of day developers are most productive. This one also takes the usual argumemts, the defaults are `time_range=None, locc_metric='change-size-cos'`. You can choose between `'sum'` and `'mean'` for aggregating the data over the specified time range (or entire project if time range is None). Using the sum helps see when the bulk of the contributions are made, while `mean` reveals more fine-grained periods of high average productivity better.

# In[ ]:


df = vis.plot_zone_heatmap(agg='mean')


# In[ ]:


df = vis.plot_zone_heatmap(agg='sum')


# ## Did anything unusual happen in 2020?
# This specific function looks at how 2020 contributions compare with the average (and the previous year).
# 
# We use the day-time heatmap again, zooming to specific years, in this case, 2019 and 2020. With `sum`, we see when most of the changes were made, while `mean` reveals when people are most productive.

# In[ ]:


import matplotlib.pyplot as plt
fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(20,8))
vis.set_year(2019)
df_2019 = vis.plot_zone_heatmap(time_range='year',fig_ax_pair = (fig,axes[0]),agg='mean')
vis.set_year(2020)
df_2020 = vis.plot_zone_heatmap(time_range='year',fig_ax_pair = (fig,axes[1]),agg='mean')


# In[ ]:


import matplotlib.pyplot as plt
fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(20,8))
vis.set_year(2019)
df_2019 = vis.plot_zone_heatmap(time_range='year',fig_ax_pair = (fig,axes[0]),agg='sum')
vis.set_year(2020)
df_2020 = vis.plot_zone_heatmap(time_range='year',fig_ax_pair = (fig,axes[1]),agg='sum')


# In[ ]:


vis.how_was_2020('change-size-cos')


# In[ ]:


vis.how_was_2020('locc')

