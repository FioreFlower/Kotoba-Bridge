; Unsigned development candidate with source-built Tesseract and Japanese OCR model.
[Setup]
AppId=KotobaBridgePrototype
AppName=Kotoba Bridge
AppVersion=0.4.0
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

[Code]
function InitializeUninstall(): Boolean;
var Code: Integer;
begin
  Result := True;
  if not UninstallSilent then
  begin
    if MsgBox('다운로드 모델을 함께 제거하려면 먼저 모델 관리 창에서 개별 삭제하세요.' + #13#10 +
      'API 키, 설정, 복습 카드는 프로그램 제거로 삭제하지 않습니다. 키는 앱의 API 키 지우기, 카드는 별도 파일 관리가 필요합니다.' + #13#10 +
      '지금 모델 관리 창을 열까요? 닫으면 프로그램 제거를 계속합니다.', mbConfirmation, MB_YESNO) = IDYES then
    begin
      if not Exec(ExpandConstant('{app}\KotobaBridge.exe'), '--manage-models', '', SW_SHOWNORMAL, ewWaitUntilTerminated, Code) then
        MsgBox('모델 관리 창을 열지 못했습니다. 모델은 보존합니다. 설치 안내의 데이터 위치를 확인하세요.', mbInformation, MB_OK);
    end;
  end;
end;
