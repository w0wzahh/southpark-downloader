#define MyAppName "South Park Downloader"
#define MyAppVersion "3.7.3"
#define MyAppPublisher "South Park Downloader contributors"
#define MyAppExeName "SouthParkDownloader.exe"

[Setup]
AppId={{9B9B5C7C-3F12-4A7D-9C2E-2D6E5F1F5E37}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\South Park Downloader
DefaultGroupName={#MyAppName}
OutputDir=..\dist\installer
OutputBaseFilename=SouthParkDownloader-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\SouthParkDownloader.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent