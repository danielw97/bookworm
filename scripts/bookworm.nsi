!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"
Unicode true
CRCCheck on
ManifestSupportedOS all
XPStyle on
Name "$%IAPP_DISPLAY_NAME%"
OutFile "$%IAPP_DISPLAY_NAME%-$%IAPP_VERSION%-$%IAPP_ARCH%-setup.exe"
InstallDir "$PROGRAMFILES\$%IAPP_DISPLAY_NAME%"
InstallDirRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\$%IAPP_NAME%" "InstallLocation"
RequestExecutionLevel admin
SetCompress auto
SetCompressor /solid lzma
SetDatablockOptimize on
VIAddVersionKey ProductName "$%IAPP_DISPLAY_NAME%"
VIAddVersionKey LegalCopyright "$%IAPP_COPYRIGHT%"
VIAddVersionKey ProductVersion "$%IAPP_VERSION%"
VIAddVersionKey FileVersion "$%IAPP_VERSION%"
VIProductVersion "$%IAPP_VERSION_EX%"
VIFileVersion "$%IAPP_VERSION_EX%"
!define MUI_ICON "builder\assets\$%IAPP_NAME%.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "builder\assets\$%IAPP_NAME%.bmp"
!define MUI_HEADERIMAGE_RIGHT
!insertmacro MUI_PAGE_WELCOME
!define MUI_LICENSEPAGE_RADIOBUTTONS
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
var StartMenuFolder
!insertmacro MUI_PAGE_STARTMENU startmenu $StartMenuFolder
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\$%IAPP_DISPLAY_NAME%.exe"
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_RESERVEFILE_LANGDLL
Section
SetShellVarContext All
SetOutPath "$INSTDIR"
File /r "$%IAPP_FROZEN_DIRECTORY%\*"
CreateShortCut "$DESKTOP\$%IAPP_DISPLAY_NAME%.lnk" "$INSTDIR\$%IAPP_DISPLAY_NAME%.exe"
!insertmacro MUI_STARTMENU_WRITE_BEGIN startmenu
CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
CreateShortCut "$SMPROGRAMS\$StartMenuFolder\$%IAPP_DISPLAY_NAME%.lnk" "$INSTDIR\$%IAPP_DISPLAY_NAME%.exe"
CreateShortCut "$SMPROGRAMS\$StartMenuFolder\$%IAPP_DISPLAY_NAME% User Manual.lnk" "$INSTDIR\resources\docs\$%IAPP_NAME%.html"
CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Uninstall $%IAPP_DISPLAY_NAME%.lnk" "$INSTDIR\Uninstall.exe"
!insertmacro MUI_STARTMENU_WRITE_END
WriteUninstaller "$INSTDIR\Uninstall.exe"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\$%IAPP_NAME%" "DisplayName" "$%IAPP_DISPLAY_NAME%"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\$%IAPP_NAME%" "UninstallString" '"$INSTDIR\uninstall.exe"'
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall" "InstallLocation" $INSTDIR
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall" "Publisher" "$%IAPP_AUTHOR%"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\$%IAPP_NAME%" "DisplayVersion" "$%IAPP_VERSION%"
WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\$%IAPP_NAME%" "VersionMajor" 0
WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\$%IAPP_NAME%" "VersionMinor" 1
WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\$%IAPP_NAME%" "NoModify" 1
WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\$%IAPP_NAME%" "NoRepair" 1
SectionEnd
Section "Uninstall"
SetShellVarContext All
DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\$%IAPP_NAME%"
RMDir /r /REBOOTOK $INSTDIR
Delete "$DESKTOP\$%IAPP_DISPLAY_NAME%.lnk"
!insertmacro MUI_STARTMENU_GETFOLDER startmenu $StartMenuFolder
RMDir /r "$SMPROGRAMS\$StartMenuFolder"
SectionEnd
Function .onInit
StrCmp $%IAPP_ARCH% "x64" +1 +2
  StrCpy $instdir "$programfiles64\$%IAPP_DISPLAY_NAME%"
FunctionEnd
