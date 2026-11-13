; Unsigned development candidate with source-built Tesseract and Japanese OCR model.
[Setup]
AppId=KotobaBridgePrototype
AppName=Kotoba Bridge
AppVersion=0.3.0
AppPublisher=Kotoba Bridge contributors
AppPublisherURL=https://github.com/FioreFlower/Kotoba-Bridge
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
LicenseFile=..\LICENSE
InfoAfterFile=installer-notice.txt
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
[Files]
Source: "..\dist\KotobaBridge\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Kotoba Bridge"; Filename: "{app}\KotobaBridge.exe"
Name: "{group}\Installation guide"; Filename: "{app}\INSTALLATION.md"
Name: "{group}\Uninstall Kotoba Bridge"; Filename: "{uninstallexe}"
[Run]
Filename: "{app}\KotobaBridge.exe"; Description: "Launch Kotoba Bridge (offline demo by default)"; Flags: nowait postinstall skipifsilent unchecked
; Intentionally no broad UninstallDelete rules: exported cards/settings outside {app}
; belong to the user and are not removed by app uninstall.
