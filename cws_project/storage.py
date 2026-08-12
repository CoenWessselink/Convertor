"""Compatibility wrapper for :mod:`cws_convertor.project.storage`."""
from cws_convertor.project.storage import *  # noqa: F401,F403

# Historical development alias; new code uses ProjectStore.
ProjectStorage = ProjectStore
