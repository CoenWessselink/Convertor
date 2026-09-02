#define MyAppName "CWS Convertor"
#define MyAppVersion "0.10.21-beta-dev"
#define MyAppNumericVersion "0.10.21.0"
#ifndef Commit7
#error Commit7 define is required for a release-bound installer
#endif
#define MyAppPublisher "CWS"
#define MyAppExeName "CWS_Convertor.exe"
#define MyCliExeName "CWS_Convertor_CLI.exe"

[Setup]
AppId={{A2B67C69-0CF8-4F50-A16A-411B02A7D9C1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\CWS Convertor
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist_installer
OutputBaseFilename=CWS_Convertor_Setup_{#MyAppVersion}_{#Commit7}_x64
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppNumericVersion}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppNumericVersion}
VersionInfoCompany={#MyAppPublisher}
ChangesAssociations=yes
UsePreviousTasks=no

[Languages]
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Maak een snelkoppeling op het bureaublad"; GroupDescription: "Snelkoppelingen:"; Flags: unchecked
Name: "fileassoc"; Description: "Koppel CWS Convertor-projecten, .nc, .nc1, .step, .stp en .ifc; voeg een PDF-contextmenu toe"; GroupDescription: "Bestandskoppelingen:"

[Files]
Source: "..\dist\CWS_Convertor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\CWS Convertor CLI"; Filename: "{app}\{#MyCliExeName}"
Name: "{group}\Verwijderen"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.cwscproj"; ValueType: string; ValueName: ""; ValueData: "CWSConvertor.Project"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CWSConvertor.Project"; ValueType: string; ValueName: ""; ValueData: "CWS Convertor-project"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CWSConvertor.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CWSConvertor.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

Root: HKA; Subkey: "Software\Classes\.nc"; ValueType: string; ValueName: ""; ValueData: "CWSConvertor.NC1"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\.nc1"; ValueType: string; ValueName: ""; ValueData: "CWSConvertor.NC1"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CWSConvertor.NC1"; ValueType: string; ValueName: ""; ValueData: "DSTV/NC1 productieonderdeel"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CWSConvertor.NC1\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CWSConvertor.NC1\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

Root: HKA; Subkey: "Software\Classes\.step"; ValueType: string; ValueName: ""; ValueData: "CWSConvertor.STEP"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\.stp"; ValueType: string; ValueName: ""; ValueData: "CWSConvertor.STEP"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CWSConvertor.STEP"; ValueType: string; ValueName: ""; ValueData: "STEP CAD-onderdeel"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CWSConvertor.STEP\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CWSConvertor.STEP\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

Root: HKA; Subkey: "Software\Classes\.ifc"; ValueType: string; ValueName: ""; ValueData: "CWSConvertor.IFC"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CWSConvertor.IFC"; ValueType: string; ValueName: ""; ValueData: "IFC-model"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CWSConvertor.IFC\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\CWSConvertor.IFC\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

; Laat de standaard PDF-lezer intact; voeg alleen een expliciete CWS Convertor-actie toe.
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\CWSConvertor"; ValueType: string; ValueName: ""; ValueData: "Openen in CWS Convertor"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\CWSConvertor\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Start {#MyAppName}"; Flags: nowait postinstall skipifsilent
