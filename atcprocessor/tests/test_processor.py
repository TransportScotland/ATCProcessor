import os
from distutils import dir_util

import pytest
import pandas as pd

from .. import processor

@pytest.fixture
def datadir(tmpdir, request):
    """
    Copies the directory containing test files to a location for further use.
    """
    filename = request.module.__file__
    test_dir, _ = os.path.split(filename)
    dir_util.copy_tree(os.path.join(test_dir, 'test files'), str(tmpdir))

    return tmpdir


class TestProcessor:
    @pytest.fixture(autouse=True)
    def setup(self, tmpdir_factory, datadir):
        self.output_folder = tmpdir_factory.mktemp('Outputs')

        self.datadir = datadir

        self.thresholds = processor.Thresholds(
            path_to_csv=os.path.join(datadir, 'thresholds.csv'),
            site_list=os.path.join(datadir, 'site list.csv')
        )

        self.count_site = processor.CountSite(
            data=os.path.join(datadir, 'sites', 'site 1 dummy data.csv'),
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
            os.path.join(self.output_folder, 'cleaned data', 'site 1.csv')
        )

        known_clean = pd.read_csv(
            os.path.join(self.datadir, 'outputs', 'cleaned data',
                         'site 1.csv')
        )

        assert cleaning_result.equals(known_clean)

