import os

import pytest

from .. import graphs

class TestGraphs:
    @pytest.fixture(autouse=True)
    def setup(self, tmpdir_factory):
        self.output_folder = tmpdir_factory.mktemp('Outputs')

    def test_make_folder(self):
        graphs.make_folder_if_necessary(self.output_folder.join('Test'))

        assert os.path.isdir(self.output_folder.join('Test'))