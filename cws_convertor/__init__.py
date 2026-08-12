"""CWS Convertor package facade.

The proven v0.5 conversion modules remain importable from the repository root.
This package introduces the stable architecture boundary used by the project,
BOM, optimisation and machine modules without replacing that working core.
"""
from .product import APP_NAME, APP_VERSION, PROJECT_SCHEMA_VERSION, display_version

__all__ = ["APP_NAME", "APP_VERSION", "PROJECT_SCHEMA_VERSION", "display_version"]
