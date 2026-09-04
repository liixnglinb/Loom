; ModelFlow 智模流水线 · Inno Setup 安装包脚本
; 生成产物：release/ModelFlow-{version}-setup.exe
; 设计要点：
;   1. 装到用户目录 %LOCALAPPDATA%\Programs\ModelFlow —— 无需管理员权限、无 UAC 弹窗
;   2. data/ 目录（数据库+工作流产物）在安装根下，升级安装自动保留（不列进卸载删除清单之外的保护靠 UninstallFilesDir 不删 data 与 *-setup.exe）
;   3. 升级静默参数 /MERGETASKS=keepsl —— 更新器复用用户上次勾选的快捷方式选项
;   4. [Run] 自动启动用 Flag: postinstall runasoriginaluser shallowinstall + --relaunch 参数，
;      静默升级（/restart）时把前台旧实例平滑替换为新版
;   5. 卸载时 data/（用户数据）与 setup 缓存保留，卸载后重装数据还在

#define MyAppName "ModelFlow 智模流水线"
#define MyAppExe "ModelFlow.exe"
#ifndef MyAppVersion
#define MyAppVersion "0.5.3"
#endif

[Setup]
AppId={{8F6C3B2A-5D1E-4A7C-9B4F-MODELFLOW0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
DefaultDirName={localappdata}\Programs\ModelFlow
UsePreviousAppDir=yes
DirExistsWarning=no
DisableProgramGroupPage=yes
; 用户级安装：privilegesRequired=lowest —— 无 UAC，装进 LOCALAPPDATA
PrivilegesRequired=lowest
OutputDir=release
OutputBaseFilename=ModelFlow-{#MyAppVersion}-setup
SetupIconFile=modelflow.ico
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
RestartApplications=no
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExe}

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: checkedonce
Name: "startmenuicon"; Description: "创建开始菜单快捷方式"; GroupDescription: "附加任务："; Flags: checkedonce unchecked

[Files]
; 主程序（PyInstaller onedir 产物，dist_app\ModelFlow\ 全树）
Source: "dist_app\ModelFlow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: startmenuicon
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Run]
; 安装完成自动启动（仅交互安装时显示勾选框；静默升级走 --relaunch 拉起新版）
Filename: "{app}\{#MyAppExe}"; Parameters: "--relaunch"; \
  Description: "立即启动 {#MyAppName}"; \
  Flags: nowait postinstall skipifsilent runasoriginaluser
[UninstallDelete]
; 卸载不删 data/（用户数据）——这里只清理运行临时文件
Type: files; Name: "{app}\data\update\update.bat"

[Messages]
SetupAppTitle=安装 - {#MyAppName} {#MyAppVersion}
WelcomeLabel2=这将安装 [name/ver] 到你的电脑。%n%n本软件安装在你自己的用户目录，不需要管理员权限。%n%n运行中的 ModelFlow 会被自动关闭后继续安装。
SelectDirDesc=安装位置
SelectDirLabel3=安装程序将把 [name] 安装到以下文件夹。%n%n升级安装会保留你的全部数据（工作流/授权/产物）。%n%n点击"浏览"可自定义安装位置。
SelectTasksLabel2=选择要创建的快捷方式（升级安装时沿用上次选择）
FinishedLabelNoIcons=[name] 已安装。%n%n可从开始菜单或直接运行 {app}\{#MyAppExe} 启动。
FinishedLabel=[name] 已安装。%n%n点击"完成"后将启动软件。

[Code]
// 温和关闭运行中的 ModelFlow：先正常退出（taskkill 不带 /F），等 3s，
// 仍在则强杀（带 /F）。避免"应用已经打开"阻断安装。
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  I: Integer;
begin
  if CurStep = ssInstall then
  begin
    Exec(ExpandConstant('{cmd}'), '/C taskkill /IM ModelFlow.exe /T',
         '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    for I := 1 to 6 do
    begin
      if Exec(ExpandConstant('{cmd}'), '/C tasklist /FI "IMAGENAME eq ModelFlow.exe" | find /I "ModelFlow.exe"',
              '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      begin
        if ResultCode <> 0 then
          Break;   // find 没匹配到 → 进程已退出
      end;
      Sleep(500);
    end;
    // 仍在运行（极端情况）→ 强杀
    Exec(ExpandConstant('{cmd}'), '/C taskkill /IM ModelFlow.exe /T /F',
         '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
