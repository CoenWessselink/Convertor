; Compile only through build-installer.ps1, using the frozen tested payload.
#ifndef PayloadDir
  #error PayloadDir must be supplied by build-installer.ps1
#endif
#ifndef OutputDir
  #error OutputDir must be supplied by build-installer.ps1
#endif
#ifndef ManifestFile
  #error ManifestFile must be supplied by build-installer.ps1
#endif
#ifndef SourceCommit
  #error SourceCommit must be supplied by build-installer.ps1
#endif
#define AppExe "Cws.TeklaBridge.exe"

[Setup]
AppId=CWS.TeklaBridge
AppName=CWS Tekla Bridge
AppVersion=0.1.0
AppVerName=CWS Tekla Bridge v0.1 ({#Copy(SourceCommit, 1, 8)})
AppPublisher=CWS
DefaultDirName={localappdata}\Programs\CWS\TeklaBridge
DefaultGroupName=CWS Tekla Bridge
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=CWS_Tekla_Bridge_v0.1_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName=CWS Tekla Bridge v0.1
VersionInfoVersion=0.1.0.0
VersionInfoTextVersion=0.1.0+{#SourceCommit}
VersionInfoDescription=CWS Tekla Bridge per-user installer
CloseApplications=no
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"

[Tasks]
Name: "desktopicon"; Description: "Snelkoppeling op het bureaublad maken"; GroupDescription: "Snelkoppelingen:"; Flags: unchecked

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ManifestFile}"; DestDir: "{app}"; DestName: "INSTALLER_PAYLOAD_MANIFEST.json"; Flags: ignoreversion

[Icons]
Name: "{group}\CWS Tekla Bridge"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{userdesktop}\CWS Tekla Bridge"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "CWS Tekla Bridge starten"; Flags: nowait postinstall skipifsilent

; No UninstallDelete section: shared settings, journals, review decisions and
; prior script-installed versions under LocalAppData\CWS\TeklaBridge are retained.
[Code]
function InitializeSetup: Boolean;
begin
  Result := IsDotNetInstalled(net48, 0);
  if not Result then
    SuppressibleMsgBox('Microsoft .NET Framework 4.8 of nieuwer is vereist. Installeer dit eerst via Microsoft en start deze installer opnieuw.', mbCriticalError, MB_OK, IDOK);
end;
