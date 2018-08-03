import os
from copy import deepcopy

import pytest
import pandas as pd

from .. import processor


class TestProcessor:
    @pytest.fixture(autouse=True)
    def setup(self, tmpdir_factory):
        self.output_folder = tmpdir_factory.mktemp('Outputs')
        self.datadir = os.path.join(os.path.dirname(__file__), 'test files')

        self.thresholds = processor.Thresholds(
            path_to_csv=os.path.join(self.datadir, 'thresholds.csv'),
            site_list=os.path.join(self.datadir, 'site list.csv')
        )

        self.cs_param_cols = dict(
            site_col='Site',
            count_col='Count',
            dir_col='Direction',
            date_col='Date',
            time_col='Hour'
        )

        self.count_site = processor.CountSite(
            data=os.path.join(self.datadir, 'sites', 'Site 1 Dummy Data.csv'),
            output_folder=self.output_folder,
            thresholds=self.thresholds,
            hour_only=True,
            **self.cs_param_cols
        )

    def test_count_site_missing_file(self):
        with pytest.raises(Exception):
            processor.CountSite(
                data=os.path.join(self.datadir, 'sites', 'NOT A FILE'),
                output_folder=self.output_folder,
                thresholds=self.thresholds,
                **self.cs_param_cols
            )

    def test_count_site_missing_column(self):
        """
        Test whether columns being missing correctly raises an error
        """
        for col in self.cs_param_cols.keys():
            temp_cols = deepcopy(self.cs_param_cols)
            temp_cols[col] += 'nope'

            print(col)
            with pytest.raises(ValueError):
                processor.CountSite(
                    data=os.path.join(self.datadir, 'sites',
                                      'Site 1 Dummy Data.csv'),
                    output_folder=self.output_folder,
                    thresholds=self.thresholds,
                    hour_only=True,
                    **temp_cols
                )

    def test_cleaning(self):
        self.count_site.clean_data()
        cleaning_result = pd.read_csv(
            os.path.join(self.output_folder, 'Cleaned Data', 'Site 1.csv')
        )

        known_clean = pd.read_csv(
            os.path.join(self.datadir, 'outputs', 'Cleaned Data',
                         'Site 1.csv')
        )

        assert cleaning_result.equals(known_clean)

