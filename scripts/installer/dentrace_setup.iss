// DENTRACE Desktop Installer — Inno Setup Script
// Target: Windows 11 x64
#define MyAppName "DENTRACE"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "DENTRACE Clinical Decision Support"
#define MyAppExeName "launch_dentrace.bat"
#define MySourceDir "C:\mini\dist\DENTRACE-v0.1.0-win64"

[Setup]
AppId={{A8F24C71-934E-4BC9-9A07-7FE382B14912}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile={#MySourceDir}\README.md
PrivilegesRequired=lowest
OutputDir=C:\mini\dist
OutputBaseFilename=DENTRACE-v0.1.0-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Filename: "{app}\{#MyAppExeName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\*.tmp"
// Retain user patient records in %LOCALAPPDATA%\DENTRACE on uninstall!
