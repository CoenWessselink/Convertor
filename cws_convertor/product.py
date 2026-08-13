"""Central product identity and compatibility constants for CWS Convertor.

This module is the only source of truth for visible names, package names and
version numbers.  Legacy payload markers intentionally stay unchanged so that
v0.4/v0.5 IFC and Trusted PDF files remain readable.
"""
from __future__ import annotations

APP_NAME = "CWS Convertor"
APP_SHORT_NAME = APP_NAME
APP_SLUG = "CWS_Convertor"
APP_ID = "nl.cws.convertor"
# Integration snapshot for Codex: semantic import, classification/BOM and
# draft production-package export are merged. Part Workbench and complete
# external-feature validation remain later release gates.
APP_VERSION = "0.8.0-alpha-dev"
APP_VERSION_NUMERIC = "0.8.0.0"
APP_PUBLISHER = "CWS"
APP_DESCRIPTION = (
    "AI-ondersteunde NC1/DSTV-, STEP-, IFC- en technische PDF-convertor"
)

CLI_EXE_NAME = "CWS_Convertor_CLI.exe"
GUI_EXE_NAME = "CWS_Convertor.exe"
DISTRIBUTION_DIRECTORY = "CWS_Convertor"
DEFAULT_OUTPUT_FOLDER = "CWS_Convertor_Output"
DEFAULT_PROJECT_FOLDER = "CWS Convertor Projects"

PROJECT_FILE_EXTENSION = ".cwscproj"
PROJECT_PACKAGE_FORMAT = "CWS_CWSC_PROJECT_V1"
PROJECT_SCHEMA_VERSION = "2.3"
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
