"""Central CWS Convertor identity and compatibility constants.

This module is the only source of truth for visible product names, package names
and versions. Legacy payload markers intentionally remain stable so historical
projects, trusted PDFs, automation and file associations continue to open while
the unified product presents one consistent CWS Convertor identity.
"""
from __future__ import annotations

APP_NAME = "CWS Convertor"
APP_SHORT_NAME = APP_NAME
# Compatibility identifiers are deliberately not renamed in stored payloads.
LEGACY_APP_NAME = "SteelConverter"
APP_SLUG = "CWS_Convertor"
APP_ID = "nl.cws.convertor"
# Unified Viewer V15 + Convertor + Scribing integration line. Project Model
# 2.25 losslessly ingests both the GitHub 2.5 line and frozen M18 2.24 authority.
APP_VERSION = "0.10.12-beta-dev"
APP_VERSION_NUMERIC = "0.10.12.0"
APP_PUBLISHER = "CWS"
APP_DESCRIPTION = "Gevalideerde staalmodel-, productie- en conversieomgeving"

CLI_EXE_NAME = "CWS_Convertor_CLI.exe"
GUI_EXE_NAME = "CWS_Convertor.exe"
DISTRIBUTION_DIRECTORY = "CWS_Convertor"
DEFAULT_OUTPUT_FOLDER = "CWS_Convertor_Output"
DEFAULT_PROJECT_FOLDER = "CWS Convertor Projects"

PROJECT_FILE_EXTENSION = ".cwscproj"
PROJECT_PACKAGE_FORMAT = "CWS_CWSC_PROJECT_V1"
PROJECT_SCHEMA_VERSION = "2.25"
PROJECT_STORAGE_VERSION = 1
CANONICAL_PART_SCHEMA_VERSION = "1.1"

INSTALLER_BASENAME = f"CWS_Convertor_Setup_{APP_VERSION}_x64"
PORTABLE_BASENAME = f"CWS_Convertor_Portable_{APP_VERSION}_x64.zip"
USER_AGENT = f"CWS-Convertor/{APP_VERSION}"

# Deliberately stable compatibility identifiers.
LEGACY_PAYLOAD_MARKER = "NC1_STEP_CONVERTER_PAYLOAD_V1"
TRUSTED_PDF_FORMAT = "NC1_STEP_IFC_TRUSTED_PDF_V1"


def display_version() -> str:
    return f"{APP_NAME} {APP_VERSION}"


__all__ = [name for name in globals() if name.isupper()] + ["display_version"]
