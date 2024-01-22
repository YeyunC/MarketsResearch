import os


def get_project_root():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return project_root
