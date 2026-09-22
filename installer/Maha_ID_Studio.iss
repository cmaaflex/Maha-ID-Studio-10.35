#define MyAppName "MAHA ID SOFTWARE"
#define MyAppVersion "10.35"
#define MyAppPublisher "SEEMA DIGITAL"
#define MyAppExeName "MAHA ID SOFTWARE 10.35.exe"

[Setup]
AppId={{281D2A77-F8D9-45F3-A579-10350000C0DE}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://www.instagram.com/seemadigital9/
AppSupportURL=mailto:cmaaflex@gmail.com
DefaultDirName={localappdata}\Programs\Seema Digital\Maha ID Studio 10.35
DefaultGroupName=SEEMA DIGITAL 10.35
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=MAHA ID SOFTWARE 10.35 Setup
SetupIconFile=..\assets\Seema_Digital_Print.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardImageFile=installer_assets\wizard_large.bmp
WizardSmallImageFile=installer_assets\wizard_small.bmp
DisableWelcomePage=no
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion=10.35.0.0
VersionInfoCompany=SEEMA DIGITAL
VersionInfoDescription=SEEMA DIGITAL Maha ID Studio Installer
VersionInfoProductName=MAHA ID SOFTWARE
VersionInfoProductVersion=10.35.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\MAHA ID SOFTWARE 10.35 Remover.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\release_files\HOW TO USE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\release_files\PRINT SETTINGS.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\release_files\Seema Digital Logo.png"; DestDir: "{app}\Brand"; Flags: ignoreversion
Source: "..\release_files\Seema Digital Splash.jpg"; DestDir: "{app}\Brand"; Flags: ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Icons]
Name: "{group}\Maha ID Studio"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Maha ID Studio 10.35"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{group}\Maha ID Studio Remover"; Filename: "{app}\MAHA ID SOFTWARE 10.35 Remover.exe"; WorkingDir: "{app}"; IconFilename: "{app}\MAHA ID SOFTWARE 10.35 Remover.exe"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Maha ID Studio"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard;
begin
  WizardForm.Caption := 'SEEMA DIGITAL â€” Maha ID Studio Setup';
  WizardForm.WelcomeLabel1.Caption := 'Welcome to Maha ID Studio';
  WizardForm.WelcomeLabel2.Caption := 'SEEMA DIGITAL professional Maha ID crop, preview and print software.' + #13#10 + #13#10 +
    '4x6 and A4 batch printing â€¢ Exact 90 x 57 mm cards â€¢ Live preview â€¢ Crop and enhancement tools';
  WizardForm.FinishedHeadingLabel.Caption := 'Maha ID Studio is ready';
  WizardForm.FinishedLabel.Caption := 'Installation completed successfully. You can launch the software now.';
end;
