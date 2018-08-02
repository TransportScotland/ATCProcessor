import os
from distutils import dir_util

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

        self.count_site = processor.CountSite(
            data=os.path.join(self.datadir, 'sites', 'Site 1 Dummy Data.csv'),
            output_folder=self.output_folder,
            site_col='Site',
            count_col='Count',
            dir_col='Direction',
            date_col='Date',
            time_col='Hour',
            hour_only=True,
            thresholds=self.thresholds
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

