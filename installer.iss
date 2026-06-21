; Inno Setup — установщик ChatList.
; Версия передаётся при сборке: iscc /DAppVersion=<версия> installer.iss

#ifndef AppVersion
  #define AppVersion "dev"
#endif

#define MyAppName "ChatList"
#define MyAppExeName "4-ChatList-" + AppVersion + ".exe"
#define MyAppPublisher "ChatList"
#define MyAppURL "https://github.com"

[Setup]
AppId={{A3B8C4D1-5E6F-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=dist
OutputBaseFilename=ChatList-Setup-{#AppVersion}
SetupIconFile=assets\chatlist.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=no
Uninstallable=yes
CreateUninstallRegKey=yes
UninstallDisplayName={#MyAppName} {#AppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallFilesDir={app}
CloseApplications=yes
CloseApplicationsFilter=4-ChatList-*.exe

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать значок на рабочем столе"; GroupDescription: "Дополнительно:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Создать значок в панели быстрого запуска"; GroupDescription: "Дополнительно:"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env.example"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "README.md"; DestDir: "{app}"; DestName: "README.txt"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Запуск {#MyAppName}"
Name: "{group}\Документация"; Filename: "{app}\README.txt"
Name: "{group}\Удалить {#MyAppName}"; Filename: "{uninstallexe}"; Comment: "Удаление программы"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden; RunOnceId: "StopChatList"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"; Check: ShouldDeleteUserData
Type: files; Name: "{app}\chatlist.db"; Check: ShouldDeleteUserData
Type: files; Name: "{app}\.env"; Check: ShouldDeleteUserData

[Code]
var
  DeleteUserData: Boolean;

function ShouldDeleteUserData(): Boolean;
begin
  Result := DeleteUserData;
end;

function InitializeUninstall(): Boolean;
var
  Answer: Integer;
begin
  Answer := MsgBox(
    'Удалить пользовательские данные?' + #13#10 +
    '• chatlist.db — база промтов и результатов' + #13#10 +
    '• logs — журнал запросов' + #13#10 +
    '• .env — ключи API',
    mbConfirmation,
    MB_YESNOCANCEL
  );

  if Answer = IDCANCEL then
  begin
    Result := False;
    Exit;
  end;

  DeleteUserData := (Answer = IDYES);
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if DeleteUserData then
      MsgBox('Программа и пользовательские данные удалены.', mbInformation, MB_OK)
    else
      MsgBox('Программа удалена. Файлы данных в каталоге установки сохранены.', mbInformation, MB_OK);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  if Exec(ExpandConstant('{sys}\taskkill.exe'), ExpandConstant('/F /IM {#MyAppExeName}'), '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Sleep(500);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;
