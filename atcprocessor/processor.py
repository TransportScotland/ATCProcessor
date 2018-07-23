import os

import pandas as pd
import numpy as np

from .graphs import yearly_scatter, calendar_plot


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
    def __init__(self, data, thresholds, output_folder,
                 site_col, count_col, dir_col,
                 date_col, time_col=None,
                 combined_datetime=False, hour_only=False):

        assert type(thresholds) == Thresholds
        self.thresholds = thresholds

        if not os.path.isdir(output_folder):
            os.mkdir(output_folder)
        self.output_folder = output_folder

        if type(data) == pd.DataFrame:
            self.data = data
        else:
            self.data = pd.read_csv(data)

        if not combined_datetime and not time_col:
            raise ValueError(
                'time_col must be specified when combined_datetime=False'
            )

        # Check columns are present
        check_cols = [site_col, count_col, dir_col, date_col, time_col]
        missing_cols = [c for c in check_cols if c not in self.data.columns]

        if missing_cols:
            raise ValueError(
                'The following columns are missing from the input data:\n' +
                '\n'.join(missing_cols)
            )
        self.site_col = site_col
        self.count_col = count_col
        self.dir_col = dir_col

        self.data[self.site_col] = self.data[self.site_col].astype(str)

        self.data[self.dir_col].replace({'N_R': 'S',
                                         'S_R': 'N',
                                         'E_R': 'W',
                                         'W_R': 'E'}, inplace=True)

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
        
        self.data['Hour'] = self.data['DateTime'].dt.hour

    def clean_data(self, std_range=2):
        self.data = self.data.groupby([self.site_col, 'DateTime',
                                       'Date', 'Hour',
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
        # TODO refine this? Average by hour by day of week?
        hourly_avg = valid_data.groupby([self.site_col, 'Hour', self.dir_col])\
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
                os.path.join(save_folder, '{}.csv'.format(site))
            )

    def cleaned_scatter(self):
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

        # Set up save folder
        save_folder = os.path.join(
            self.output_folder, 'Cleaned Scatter Plots'
        )

        if not os.path.isdir(save_folder):
            os.mkdir(save_folder)

        # For each site, generate and save the scatter plots
        for site_name, site_data in self.data.groupby(self.site_col):
            figures = yearly_scatter(site_data, datetime_col='DateTime',
                                     value_col=self.count_col,
                                     category_col='Status',
                                     colour_col='ScatterColour',
                                     dir_col=self.dir_col)

            for year, fig in figures:
                fig.savefig(
                    os.path.join(
                        save_folder, '{}_{}.png'.format(site_name, year)
                    ),
                    bbox_inches='tight'
                )

    def produce_cal_plots(self, valid_only=True, by_direction=True):
        if valid_only:
            save_folder = os.path.join(
                self.output_folder, 'Cleaned Calendar Plots'
            )
            plot_data = self.data[self.data['Valid']]
        else:
            save_folder = os.path.join(
                self.output_folder, 'Uncleaned Calendar Plots'
            )
            plot_data = self.data

        grouping = [self.site_col]

        if by_direction:
            grouping.append(self.dir_col)

        if not os.path.isdir(save_folder):
            os.mkdir(save_folder)

        plot_data = plot_data.groupby(grouping + ['Date'],
                                      as_index=False)\
                             .agg({self.count_col: 'sum'})\
                             .set_index('Date') \
                             .groupby(grouping)

        # For each site and direction, generate and save the calendar plot
        for grp, site_data in plot_data:
            figures = calendar_plot(site_data, count_column=self.count_col)

            if by_direction:
                out_name = '_'.join(grp)
            else:
                out_name = '{}_Total'.format(grp)

            for fig, ax in figures:
                fig.savefig(
                    os.path.join(
                        save_folder, '{}.png'.format(out_name)
                    ),
                    bbox_inches='tight'
                )
