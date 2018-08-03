import os
import calendar
from itertools import chain, combinations

import pandas as pd
import numpy as np

from .graphs import yearly_scatter, calendar_plot, atc_facet_grid


class SiteList:
    def __init__(self, path_to_csv):
        self.data = pd.read_csv(path_to_csv)
        self.categories = set(c for c in self.data.columns
                              if not c.lower().startswith('site'))

        # TODO make sure "High" and "Low" aren't in columns
        # TODO make sure there's only one column that starts with "Site". Remember it.


class Thresholds:
    def __init__(self, path_to_csv, site_list):
        thresholds = pd.read_csv(path_to_csv)
        if not type(site_list) == SiteList:
            site_list = SiteList(site_list)

        # Check high and low columns are present
        if not all(c in thresholds.columns for c in ('Low', 'High')):
            raise ValueError(
                'Thresholds must contain the columns "Low" and "High"'
            )

        # Check all category columns present
        category_columns = set(c for c in thresholds.columns
                               if c not in ('Hour', 'Month', 'Low', 'High'))

        if not category_columns.issubset(site_list.categories):
            raise ValueError(
                'Thresholds features the following columns not included '
                'in the site list:\n'
                + '\n'.join(category_columns - site_list.categories)
            )

        # Check all possible category combinations are present
        shared_cats = list(
            site_list.categories.intersection(category_columns)
        )

        unique_cat_vals = thresholds.groupby(shared_cats)\
                                    .size()\
                                    .reset_index()[shared_cats]

        sites_unique_cat_vals = site_list.data.groupby(shared_cats)\
                                              .size()\
                                              .reset_index()[shared_cats]

        mut_cat_vals = pd.merge(unique_cat_vals, sites_unique_cat_vals,
                                indicator=True, how='outer')

        # Selecting right_only tells us what values are missing from thresholds
        missing_cat_vals = mut_cat_vals[mut_cat_vals['_merge'] == 'right_only']

        # If we're missing categories, raise the error
        if not missing_cat_vals.empty:
            raise ValueError(
                'The following category combinations listed in the site list '
                'are missing from the thresholds:\n' +
                missing_cat_vals[shared_cats].to_string(index=False)
            )

        # Otherwise, all is good and we can merge the two together
        # Use how='right' to ensure we get possible Hour/Month etc columns
        self.data = site_list.data.merge(thresholds, how='right')


class CountSite:
    def __init__(self, data, output_folder,
                 site_col, count_col, dir_col,
                 date_col, time_col=None,
                 combined_datetime=False, hour_only=False, thresholds=None):

        if thresholds:
            assert type(thresholds) == Thresholds
        self.thresholds = thresholds

        if not os.path.isdir(output_folder):
            os.mkdir(output_folder)
        self.output_folder = output_folder

        if type(data) == pd.DataFrame:
            self.data = data
        else:
            if not os.path.isfile(data):
                raise FileNotFoundError('Data file does not seem to exist.')
            self.data = pd.read_csv(data)

        if not combined_datetime and not time_col:
            raise ValueError(
                'time_col must be specified when combined_datetime=False'
            )

        # Check columns are present
        check_cols = [site_col, count_col, dir_col, date_col]
        if not combined_datetime:
            check_cols.append(time_col)
        missing_cols = [c for c in check_cols if c not in self.data.columns]

        if missing_cols:
            raise ValueError(
                'The following columns are missing from the input data:\n' +
                '\n'.join(missing_cols)
            )

        if site_col not in thresholds.data.columns:
            raise ValueError(
                'Site identifying column "{}" must be the same in both ' +
                'the data file and site list file'.format(site_col)
            )

        self.site_col = site_col
        self.count_col = count_col
        self.dir_col = dir_col

        self.data[self.site_col] = self.data[self.site_col].astype(str)

        self.data[self.dir_col].replace({'N_R': 'S',
                                         'S_R': 'N',
                                         'E_R': 'W',
                                         'W_R': 'E'}, inplace=True)

        self.__convert_datetimes(combined_datetime, date_col, time_col,
                                 hour_only)

    def __convert_datetimes(self, combined_datetime, date_col, time_col,
                            hour_only):
        if combined_datetime:
            self.data['DateTime'] = self.data[date_col]
            self.data['Date'] = self.data['DateTime'].dt.date
        else:
            if hour_only:
                time_vals = pd.to_timedelta(self.data[time_col], unit='h')
            else:
                time_vals = pd.to_timedelta(self.data[time_col])
            self.data['Date'] = pd.to_datetime(self.data[date_col])
    
            self.data['DateTime'] = self.data['Date'] + time_vals

        self.data['Year'] = self.data['Date'].dt.year
        self.data['Month'] = pd.Categorical(
            self.data['Date'].dt.month_name(),
            categories=calendar.month_name[1:], ordered=True
        )
        self.data['WeekNumber'] = self.data['Date'].dt.week
        self.data['Day'] = pd.Categorical(
            self.data['Date'].dt.weekday_name,
            categories=calendar.day_name, ordered=True
        )
        self.data['Hour'] = self.data['DateTime'].dt.hour

    def clean_data(self, std_range=2):
        print('Cleaning...')
        if not self.thresholds:
            raise ValueError(
                'Thresholds required to clean data'
            )
        self.data = self.data.groupby([self.site_col, 'DateTime',
                                       'Date', 'Year', 'Month', 'WeekNumber',
                                       'Day', 'Hour',
                                       self.dir_col], as_index=False) \
            .agg({self.count_col: 'sum'})

        # Get the thresholds alongside the relevant counts
        combined_thresh = self.data.merge(
            self.thresholds.data, how='left'
        )[[self.count_col, 'Low', 'High']]

        # Flag low or high counts
        low_count = combined_thresh[self.count_col] < combined_thresh['Low']
        high_count = combined_thresh[self.count_col] > combined_thresh['High']

        # Add in column to report meeting or failing thresholds
        self.data['ThreshCheck'] = np.select([low_count, high_count], [-1, 1],
                                             default=0)

        # Work out instances where day total is 0 - probably a fault
        daily_total = self.data.groupby('Date', as_index=False)\
                               .agg({self.count_col: 'sum'})

        daily_total['MissingDay'] = (daily_total[self.count_col] == 0)*1
        daily_total = daily_total[['Date', 'MissingDay']]

        self.data = self.data.merge(daily_total)

        # Flag valid where Threshold Check is passed and day isn't totally
        # missing
        self.data['Valid'] = (self.data['ThreshCheck'].abs()
                              + self.data['MissingDay']) == 0

        valid_data = self.data[self.data['Valid']]

        # Work out the average hourly flow in that direction at the site
        hourly_avg = valid_data.groupby([self.site_col, 'Hour', 'Day',
                                         self.dir_col])\
                               .agg({self.count_col: ['mean', 'std']})
        hourly_avg.columns = hourly_avg.columns.droplevel()
        hourly_avg.reset_index(inplace=True)

        # Upper and lower stdev bounds
        hourly_avg['StdMax'] = hourly_avg['mean'] + hourly_avg['std']*std_range
        hourly_avg['StdMin'] = hourly_avg['mean'] - hourly_avg['std']*std_range

        hourly_avg.drop(['mean', 'std'], axis='columns', inplace=True)

        # Bring stdev values into the data frame,
        # flag valid records with stdev warnings
        self.data = self.data.merge(hourly_avg)
        self.data['StdWarning'] = (
            self.data['Valid'] &
            ((self.data[self.count_col] < self.data['StdMin'])
             | (self.data[self.count_col] > self.data['StdMax']))
        ).astype(int)
        self.data.drop(['StdMax', 'StdMin'], axis='columns', inplace=True)

        # Sort values so they can be written out neatly
        self.data = self.data.sort_values(by=['Date',
                                              'Hour',
                                              self.dir_col])\
                             .reset_index(drop=True)

        # Save out cleaned data
        save_folder = os.path.join(self.output_folder, 'Cleaned Data')

        if not os.path.isdir(save_folder):
            os.mkdir(save_folder)

        for site, site_data in self.data.groupby(self.site_col):
            site_data.to_csv(
                os.path.join(save_folder, '{}.csv'.format(site)), index=False
            )

    def summarise_cleaned_data(self):
        # Columns to summarise over
        sum_cats = ['Year', 'Month', 'Day']

        # Get all possible combinations of the columns
        summary_options = chain(
            *map(lambda x: list(combinations(sum_cats, x)),
                 range(1, len(sum_cats)+1))
        )

        for site, site_data in self.data.groupby(self.site_col):
            # Get value counts for all combinations
            all_counts = []
            for grp in summary_options:
                df = site_data.groupby(by=list(grp))['Valid']\
                              .value_counts()\
                              .reset_index(name='Freq')\
                              .pivot_table(index=grp, columns='Valid',
                                           values='Freq')\
                              .reset_index()
                all_counts.append(df)

            summaries = pd.concat(all_counts, ignore_index=True, sort=False)\
                          .rename({True: 'Valid', False: 'Not Valid'},
                                  axis='columns')

            # First fill category NAs, then fill actual value NAs
            summaries[sum_cats] = summaries[sum_cats].fillna('All')
            summaries.fillna(0, inplace=True)

            summaries['Valid_%'] = summaries['Valid'] / (summaries['Valid']
                                                         + summaries['Not Valid'])

            # TODO improve the output name and location
            summaries[sum_cats + ['Valid', 'Not Valid', 'Valid_%']].to_csv(
                os.path.join(self.output_folder, '{} Cleaning Summary.csv'.format(site)),
                index=False
            )

    def cleaned_scatter(self):
        print('Scattering...')
        # Flag statuses and colours
        sd_warn = self.data['StdWarning'] != 0
        missing_day = self.data['MissingDay'] == 1
        too_low = self.data['ThreshCheck'] == -1
        too_high = self.data['ThreshCheck'] == 1

        self.data['Status'] = np.select(
            [sd_warn, missing_day, too_low, too_high],
            ['Warning - Outside SD Range',
             'Full day missing',
             'Below threshold',
             'Above threshold'],
            default='Valid'
        )

        issue_colours = {
            'Warning - Outside SD Range': 'darkorange',
            'Full day missing': 'grey',
            'Below threshold': 'black',
            'Above threshold': 'red',
            'Valid': 'darkturquoise'
        }

        self.data['ScatterColour'] = self.data['Status'].map(issue_colours)

        # For each site, generate and save the scatter plots
        for site_name, site_data in self.data.groupby(self.site_col):
            dest = os.path.join(self.output_folder, site_name,
                                'Cleaned Scatter.png')
            yearly_scatter(site_data, datetime_col='DateTime',
                           value_col=self.count_col,
                           category_col='Status',
                           colour_col='ScatterColour',
                           dir_col=self.dir_col,
                           destination_path=dest)

    def produce_cal_plots(self, valid_only=True, by_direction=True,
                          min_hours=1):
        print('Calendaring...')
        # Choose data and output folder depending on restricting to valid
        if valid_only:
            save_suffix = 'Cleaned'
            plot_data = self.data[self.data['Valid']]
        else:
            save_suffix = 'Uncleaned'
            plot_data = self.data

        grouping = [self.site_col]

        if by_direction:
            grouping.append(self.dir_col)

        plot_data = plot_data.groupby(grouping + ['Date'],
                                      as_index=False)\
                             .agg({self.count_col: ('sum', 'count')})\
                             .set_index('Date') \
                             .groupby(grouping)

        # For each site and direction, generate and save the calendar plot
        for grp, site_data in plot_data:
            if type(grp) == str:
                grp = [grp]
            site_data = site_data[
                site_data[(self.count_col, 'count')] >= min_hours
            ]

            calendar_plot(site_data,
                          count_column=(self.count_col, 'sum'),
                          destination_path=os.path.join(
                              self.output_folder, grp[0],
                              '{} {} Calendar Plot.png'.format(
                                  grp[-1] if by_direction else 'Total', save_suffix
                              )
                          )
                          )

    def facet_grids(self, valid_only=True, by_direction=True):
        print('Faceting...')

        if valid_only:
            plot_data = self.data[self.data['Valid']]
        else:
            plot_data = self.data

        suffix = ''
        hour_group = [self.site_col, 'Year', 'Day', 'Hour']
        week_group = [self.site_col, 'Year', 'Day', 'WeekNumber']
        hour_params = dict()
        week_params = dict()
        if by_direction:
            suffix += ' by direction'
            hour_group.append(self.dir_col)
            hour_params['hue'] = self.dir_col
            week_group.append(self.dir_col)
            week_params['separate_cols'] = self.dir_col
        if valid_only:
            suffix += '_Valid Only'

        if not by_direction:
            cols = [c for c in plot_data.columns
                    if c not in (self.dir_col, self.count_col)]
            plot_data = plot_data.groupby(cols, as_index=False) \
                                 .agg({self.count_col: 'sum'})
        hour_data = plot_data.groupby(hour_group, as_index=False) \
                             .agg({self.count_col: 'mean'})

        for site_name, site_data in hour_data.groupby(self.site_col):
            file_name = os.path.join(
                self.output_folder, site_name,
                'Hourly Average by Day{}.png'.format(suffix)
            )

            atc_facet_grid(site_data, separate_rows='Day',
                           separate_cols='Year',
                           x='Hour', y=self.count_col,
                           destination_path=file_name,
                           **hour_params)

        week_data = plot_data.groupby(week_group, as_index=False) \
                             .agg({self.count_col: 'sum'})

        for site_name, site_data in week_data.groupby(self.site_col):
            file_name = os.path.join(
                self.output_folder, site_name,
                'Week Total by Day{}.png'.format(suffix)
            )
            atc_facet_grid(site_data, separate_rows='Day',
                           x='WeekNumber', y=self.count_col,
                           hue='Year',
                           destination_path=file_name,
                           **week_params
                           )

