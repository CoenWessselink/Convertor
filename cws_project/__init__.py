"""Compatibility facade for the CWS Convertor project package.

The canonical implementation lives in :mod:`cws_convertor.project`.  This
namespace remains importable for early v0.6 development builds and third-party
scripts, but no second project model is maintained.
"""
from cws_convertor.project import *  # noqa: F401,F403
