#define MyAppName "SteelConverter"
#define MyAppVersion "0.8.3-beta-dev"
#define MyAppNumericVersion "0.8.3.0"
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
OutputBaseFilename=CWS_Convertor_Setup_{#MyAppVersion}_x64
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppNumericVersion}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppNumericVersion}
VersionInfoCompany={#MyAppPublisher}
ChangesAssociations=yes

[Languages]
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Maak een snelkoppeling op het bureaublad"; GroupDescription: "Snelkoppelingen:"; Flags: unchecked
Name: "fileassoc"; Description: "Koppel SteelConverter-projecten, .nc, .nc1, .step, .stp en .ifc; voeg een PDF-contextmenu toe"; GroupDescription: "Bestandskoppelingen:"; Flags: checkedonce

[Files]
Source: "..\dist\CWS_Convertor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\SteelConverter CLI"; Filename: "{app}\{#MyCliExeName}"
Name: "{group}\Verwijderen"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCR; Subkey: ".cwscproj"; ValueType: string; ValueName: ""; ValueData: "CWSConvertor.Project"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: "CWSConvertor.Project"; ValueType: string; ValueName: ""; ValueData: "SteelConverter-project"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "CWSConvertor.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: fileassoc
Root: HKCR; Subkey: "CWSConvertor.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

Root: HKCR; Subkey: ".nc"; ValueType: string; ValueName: ""; ValueData: "CWSConvertor.NC1"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".nc1"; ValueType: string; ValueName: ""; ValueData: "CWSConvertor.NC1"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: "CWSConvertor.NC1"; ValueType: string; ValueName: ""; ValueData: "DSTV/NC1 productieonderdeel"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "CWSConvertor.NC1\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: fileassoc
Root: HKCR; Subkey: "CWSConvertor.NC1\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

Root: HKCR; Subkey: ".step"; ValueType: string; ValueName: ""; ValueData: "CWSConvertor.STEP"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: ".stp"; ValueType: string; ValueName: ""; ValueData: "CWSConvertor.STEP"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: "CWSConvertor.STEP"; ValueType: string; ValueName: ""; ValueData: "STEP CAD-onderdeel"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "CWSConvertor.STEP\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: fileassoc
Root: HKCR; Subkey: "CWSConvertor.STEP\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

Root: HKCR; Subkey: ".ifc"; ValueType: string; ValueName: ""; ValueData: "CWSConvertor.IFC"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: "CWSConvertor.IFC"; ValueType: string; ValueName: ""; ValueData: "IFC-model"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "CWSConvertor.IFC\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: fileassoc
Root: HKCR; Subkey: "CWSConvertor.IFC\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

; Laat de standaard PDF-lezer intact; voeg alleen een expliciete SteelConverter-actie toe.
Root: HKCR; Subkey: "SystemFileAssociations\.pdf\shell\CWSConvertor"; ValueType: string; ValueName: ""; ValueData: "Openen in SteelConverter"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "SystemFileAssociations\.pdf\shell\CWSConvertor\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Start {#MyAppName}"; Flags: nowait postinstall skipifsilent
