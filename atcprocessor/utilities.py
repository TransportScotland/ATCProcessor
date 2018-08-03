import os


def make_folder_if_necessary(filepath):
    parent_dir = os.path.dirname(filepath)

    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
