; Windows x64 candidate installer recipe. Not compiled or tested in this delivery.
[Setup]
AppId=KotobaBridgePrototype
AppName=Kotoba Bridge
AppVersion=0.1.0
DefaultDirName={localappdata}\Programs\KotobaBridge
DefaultGroupName=Kotoba Bridge
PrivilegesRequired=lowest
MinVersion=10.0.19045
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
OutputDir=..\dist
OutputBaseFilename=KotobaBridge-Setup-x64
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\KotobaBridge.exe
[Files]
Source: "..\dist\KotobaBridge\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Kotoba Bridge"; Filename: "{app}\KotobaBridge.exe"
Name: "{group}\사용 안내"; Filename: "{app}\README.md"
[Run]
Filename: "{app}\KotobaBridge.exe"; Description: "Launch offline demo"; Flags: nowait postinstall skipifsilent
