#define AppName "SpeechDictation"
#ifndef AppVersion
  #define AppVersion "2.0.0"
#endif
#define SourceDir "..\..\dist\SpeechDictation"

[Setup]
; Its own id, so it never upgrades over or uninstalls the original GeminiSpeechAPI.
AppId={{9825FFCA-3E51-41DC-8D59-1B05FCD825B5}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppName}
DefaultDirName={localappdata}\SpeechDictation
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=SpeechDictation-Setup
SetupIconFile=..\..\assets\icon.ico
UninstallDisplayIcon={app}\SpeechDictation.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
CloseApplications=force
RestartApplications=no

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\SpeechDictation"; Filename: "{app}\SpeechDictation.exe"

[Registry]
; "Start with Windows" lives in Settings and writes this value; uninstall removes it.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "SpeechDictation"; Flags: uninsdeletevalue dontcreatekey

[Run]
Filename: "{app}\SpeechDictation.exe"; Description: "Launch SpeechDictation"; Flags: nowait postinstall skipifsilent runasoriginaluser
Filename: "{app}\SpeechDictation.exe"; Flags: nowait runasoriginaluser; Check: WizardSilent
