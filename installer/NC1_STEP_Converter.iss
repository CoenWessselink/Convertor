#define MyAppName "NC1 STEP IFC Converter"
#define MyAppVersion "0.5.0"
#define MyAppPublisher "NC1 STEP IFC Converter"
#define MyAppExeName "NC1_STEP_Converter.exe"
#define MyCliExeName "NC1_STEP_Converter_CLI.exe"

[Setup]
AppId={{A2B67C69-0CF8-4F50-A16A-411B02A7D9C1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\NC1 STEP IFC Converter
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist_installer
OutputBaseFilename=NC1_STEP_IFC_Converter_Setup_{#MyAppVersion}_x64
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
ChangesAssociations=yes

[Languages]
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Maak een snelkoppeling op het bureaublad"; GroupDescription: "Snelkoppelingen:"; Flags: unchecked
Name: "fileassoc"; Description: "Koppel .nc, .nc1, .step, .stp, .ifc en Trusted PDF aan de converter"; GroupDescription: "Bestandskoppelingen:"; Flags: checkedonce

[Files]
Source: "..\dist\NC1_STEP_Converter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Converter CLI"; Filename: "{app}\{#MyCliExeName}"
Name: "{group}\Verwijderen"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCR; Subkey: ".nc"; ValueType: string; ValueName: ""; ValueData: "NC1STEPConverter.NC1"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".nc1"; ValueType: string; ValueName: ""; ValueData: "NC1STEPConverter.NC1"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: "NC1STEPConverter.NC1"; ValueType: string; ValueName: ""; ValueData: "DSTV/NC1 productieonderdeel"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "NC1STEPConverter.NC1\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: fileassoc
Root: HKCR; Subkey: "NC1STEPConverter.NC1\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

Root: HKCR; Subkey: ".step"; ValueType: string; ValueName: ""; ValueData: "NC1STEPConverter.STEP"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".stp"; ValueType: string; ValueName: ""; ValueData: "NC1STEPConverter.STEP"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: "NC1STEPConverter.STEP"; ValueType: string; ValueName: ""; ValueData: "STEP CAD-onderdeel"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "NC1STEPConverter.STEP\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: fileassoc
Root: HKCR; Subkey: "NC1STEPConverter.STEP\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

Root: HKCR; Subkey: ".ifc"; ValueType: string; ValueName: ""; ValueData: "NC1STEPConverter.IFC"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: "NC1STEPConverter.IFC"; ValueType: string; ValueName: ""; ValueData: "IFC staalonderdeel"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "NC1STEPConverter.IFC\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: fileassoc
Root: HKCR; Subkey: "NC1STEPConverter.IFC\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Start {#MyAppName}"; Flags: nowait postinstall skipifsilent
