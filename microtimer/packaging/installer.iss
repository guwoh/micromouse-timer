#define AppName "Micromouse Timer"
#define AppVersion "1.2.2"

[Setup]
AppId=MicromouseTimer
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\Micromouse Timer
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
OutputDir=..\dist
OutputBaseFilename=MicromouseTimer-Setup-Windows
SetupIconFile=..\assets\icons\micromouse.ico
UninstallDisplayIcon={app}\MicromouseTimer.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "..\dist\MicromouseTimer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\MicromouseTimer.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\MicromouseTimer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MicromouseTimer.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
