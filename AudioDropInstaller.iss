#define MyAppName "AudioDrop"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "AudioDrop"
#define MyAppExeName "AudioDrop.exe"

[Setup]
AppId={{A9C3E06B-52D8-4D6B-9B1B-0D4A7E019D21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\AudioDrop
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer
OutputBaseFilename=AudioDropSetup_{#MyAppVersion}
SetupIconFile=assets\audiodrop_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "dist\AudioDrop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\AudioDrop"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\AudioDrop"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir AudioDrop"; Flags: nowait postinstall skipifsilent
