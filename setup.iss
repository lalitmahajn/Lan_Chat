; Inno Setup Script for LAN Chat Application
#define MyAppName "LAN Chat"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "LAN Chat Open Source"
#define MyAppURL "https://github.com/lalitmahajn/Lan_Chat"
#define ClientExeName "LAN_Chat_Client.exe"
#define ServerExeName "LAN_Chat_Server.exe"

[Setup]
AppId={{593FA80A-06DE-47D3-9F27-531C41D8EACD}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\LAN Chat
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=LAN_Chat_Setup_v1.0
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Types]
Name: "full"; Description: "Full Installation (Client + Server)"
Name: "client"; Description: "Client Only (Recommended for users)"
Name: "server"; Description: "Server Only"

[Components]
Name: "client"; Description: "LAN Chat Client App"; Types: full client; Flags: fixed
Name: "server"; Description: "LAN Chat Server App"; Types: full server

[Files]
; Client files
Source: "dist\LAN_Chat_Client\*"; DestDir: "{app}\Client"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: client
; Server files
Source: "dist\LAN_Chat_Server\*"; DestDir: "{app}\Server"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: server

[Icons]
; Start Menu Icons
Name: "{group}\LAN Chat Client"; Filename: "{app}\Client\{#ClientExeName}"; Components: client
Name: "{group}\LAN Chat Server Status"; Filename: "{app}\Server\{#ServerExeName}"; Components: server
Name: "{group}\Uninstall LAN Chat"; Filename: "{uninstallexe}"

; Desktop Shortcuts
Name: "{autodesktop}\LAN Chat"; Filename: "{app}\Client\{#ClientExeName}"; Components: client
Name: "{autodesktop}\LAN Chat Server"; Filename: "{app}\Server\{#ServerExeName}"; Components: server

[Run]
Filename: "{app}\Client\{#ClientExeName}"; Description: "Launch LAN Chat Client"; Flags: nowait postinstall skipifsilent; Components: client
