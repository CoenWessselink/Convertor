#define MyAppName "CWS Viewer"
#define MyAppVersion "1.2.0-rc3"
#define MyAppPublisher "CWS"
#define MyAppExeName "CWS_Viewer.exe"

[Setup]
AppId={{C487B489-8B65-44D8-A198-790D9D2C4C20}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\CWS\CWS Viewer
DefaultGroupName=CWS
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\release_windows
OutputBaseFilename=CWS_Viewer_Setup_{#MyAppVersion}_x64
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\dist\CWS_Viewer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CWS Viewer"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\CWS Viewer"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Bureaubladsnelkoppeling maken"; GroupDescription: "Extra opties:"

[Registry]
Root: HKCU; Subkey: "Software\Classes\.cwscproj"; ValueType: string; ValueName: ""; ValueData: "CWSViewer.Project"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\CWSViewer.Project"; ValueType: string; ValueName: ""; ValueData: "CWS Convertor Project"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\CWSViewer.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\CWSViewer.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ifc\shell\CWSViewer"; ValueType: string; ValueName: ""; ValueData: "Openen in CWS Viewer"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.ifc\shell\CWSViewer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.step\shell\CWSViewer"; ValueType: string; ValueName: ""; ValueData: "Openen in CWS Viewer"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.step\shell\CWSViewer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.stp\shell\CWSViewer"; ValueType: string; ValueName: ""; ValueData: "Openen in CWS Viewer"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.stp\shell\CWSViewer\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
