import os

import pandas as pd
import numpy as np

from .graphs import yearly_scatter


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
    def __init__(self, data, thresholds, output_folder):
        assert type(thresholds) == Thresholds
        self.thresholds = thresholds

        if not os.path.isdir(output_folder):
            os.mkdir(output_folder)
        self.output_folder = output_folder

        if type(data) == pd.DataFrame:
            self.data = data
        else:
            self.data = pd.read_csv(data)

        # TODO make flexible for "SiteName" column. What if this column is missing?
        self.data['SiteName'] = self.data['SiteName'].astype(str)

        # TODO make flexible for columns. Different names?
        self.data['DirectionName'].replace({'N_R': 'S',
                                            'S_R': 'N',
                                            'E_R': 'W',
                                            'W_R': 'E'}, inplace=True)

        self.data['DateTime'] = pd.to_datetime(self.data['IntervalStartDate'])\
                                + pd.to_timedelta(self.data['Hour'], unit='h')

        self.data = self.data.groupby(['SiteName', 'DateTime',
                                       'IntervalStartDate', 'Hour',
                                       'DirectionName'], as_index=False)\
                             .agg({'VehicleCount': 'sum'})

    def clean_data(self, std_range=2):
        # TODO make flexible for columns. Different names?
        # Get the thresholds alongside the relevant counts
        combined_thresh = self.data.merge(
            self.thresholds.data, how='left'
        )[['VehicleCount', 'Low', 'High']]

        # Flag low or high counts
        low_count = combined_thresh['VehicleCount'] < combined_thresh['Low']
        high_count = combined_thresh['VehicleCount'] > combined_thresh['High']

        # Add in column to report meeting or failing thresholds
        self.data['ThreshCheck'] = np.select([low_count, high_count], [-1, 1],
                                             default=0)

        # Work out instances where day total is 0 - probably a fault
        daily_total = self.data.groupby('IntervalStartDate', as_index=False)\
                               .agg({'VehicleCount': 'sum'})

        daily_total['MissingDay'] = (daily_total['VehicleCount'] == 0)*1
        daily_total = daily_total[['IntervalStartDate', 'MissingDay']]

        self.data = self.data.merge(daily_total)

        # Flag valid where Theshold Check is passed and day isn't totally
        # missing
        self.data['Valid'] = (self.data['ThreshCheck'].abs()
                              + self.data['MissingDay']) == 0

        valid_data = self.data[self.data['Valid']]

        # Work out the average hourly flow in that direction at the site
        # TODO refine this? Average by hour by day of week?
        hourly_avg = valid_data.groupby(['SiteName', 'Hour', 'DirectionName'])\
                               .agg({'VehicleCount': ['mean', 'std']})
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
            ((self.data['VehicleCount'] < self.data['StdMin'])
             | (self.data['VehicleCount'] > self.data['StdMax']))
        ).astype(int)
        self.data.drop(['StdMax', 'StdMin'], axis='columns', inplace=True)

        # Sort values so they can be written out neatly
        self.data = self.data.sort_values(by=['IntervalStartDate',
                                              'Hour',
                                              'DirectionName'])\
                             .reset_index(drop=True)

        # Save out cleaned data
        save_folder = os.path.join(self.output_folder, 'Cleaned Data')

        if not os.path.isdir(save_folder):
            os.mkdir(save_folder)

        for site, site_data in self.data.groupby('SiteName'):
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
            'Warning - Outside SD Range': 'orange',
            'Full day missing': 'grey',
            'Below threshold': 'black',
            'Above threshold': 'red',
            'Valid': 'green'
        }

        self.data['ScatterColour'] = self.data['Status'].map(issue_colours)

        # Set up save folder
        save_folder = os.path.join(
            self.output_folder, 'Cleaned Scatter Plots'
        )

        if not os.path.isdir(save_folder):
            os.mkdir(save_folder)

        # For each site, generate and save the scatter plots
        for site_name, site_data in self.data.groupby('SiteName'):
            figures = yearly_scatter(site_data, datetime_col='DateTime',
                                     value_col='VehicleCount',
                                     category_col='Status',
                                     colour_col='ScatterColour',
                                     dir_col='DirectionName')

            for year, fig in figures:
                fig.savefig(
                    os.path.join(
                        save_folder, '{}_{}.png'.format(site_name, year)
                    ),
                    bbox_inches='tight'
                )
