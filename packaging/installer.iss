; Inno Setup script. Build: iscc /DAppVersion=0.9.0 packaging\installer.iss
; Expects dist\Form22Generator.exe (run PyInstaller first). Output: dist\NC-Form-22-Generator-Setup.exe
#ifndef AppVersion
  #define AppVersion "0.9.0"
#endif

[Setup]
; Fixed AppId enables clean in-place upgrades.
AppId={{6B7C1E52-3F0A-4C57-9E0D-4F22A1C9B022}
; Check the app's explicit mutex instead of Restart Manager's broader file-use detection.
AppMutex=Local\NCForm22Generator-6B7C1E52-3F0A-4C57-9E0D-4F22A1C9B022
AppName=NC Form 22 Generator
AppVersion={#AppVersion}
AppVerName=NC Form 22 Generator {#AppVersion}
AppPublisher=NC Form 22 Generator Project
DefaultDirName={autopf}\NC Form 22 Generator
DefaultGroupName=NC Form 22 Generator
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\Form22Generator.exe
UninstallDisplayName=NC Form 22 Generator
OutputDir=..\dist
OutputBaseFilename=NC-Form-22-Generator-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=no
VersionInfoVersion={#AppVersion}
VersionInfoProductName=NC Form 22 Generator

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked

[Files]
; The official Form 22 template is embedded inside the executable.
Source: "..\dist\Form22Generator.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\NC Form 22 Generator"; Filename: "{app}\Form22Generator.exe"
Name: "{group}\Uninstall NC Form 22 Generator"; Filename: "{uninstallexe}"
Name: "{autodesktop}\NC Form 22 Generator"; Filename: "{app}\Form22Generator.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Form22Generator.exe"; Description: "Launch NC Form 22 Generator"; Flags: nowait postinstall skipifsilent
