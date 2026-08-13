"""Compatibility shim exposing the central SteelConverter product constants."""
from cws_convertor.product import *  # noqa: F401,F403

# Historical aliases used by the v0.5 conversion modules and build scripts.
VERSION = APP_VERSION
WINDOWS_FILE_VERSION = APP_VERSION_NUMERIC
PRODUCT_NAME = APP_NAME
PRODUCT_SLUG = APP_SLUG
PRODUCT_PUBLISHER = APP_PUBLISHER
PROJECT_EXTENSION = PROJECT_FILE_EXTENSION
OUTPUT_DIRECTORY = DEFAULT_OUTPUT_FOLDER
