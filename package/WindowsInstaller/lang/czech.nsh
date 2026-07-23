/*
VibeCAD Installer Language File
Language: Czech
*/

!insertmacro LANGFILE_EXT "Czech"

${LangFileString} TEXT_INSTALL_CURRENTUSER "(Installed for Current User)"

${LangFileString} TEXT_WELCOME "Tento pomocník vás provede instalací VibeCADu.$\r$\n\
				$\r$\n\
				$_CLICK"

#${LangFileString} TEXT_CONFIGURE_PYTHON "Compiling Python scripts..."

${LangFileString} TEXT_FINISH_DESKTOP "Create desktop shortcut"
${LangFileString} TEXT_FINISH_WEBSITE "Visit github.com/10-X-eng/vibecad for the latest news, support and tips"

#${LangFileString} FileTypeTitle "VibeCAD-dokumentů"

#${LangFileString} SecAllUsersTitle "Instalovat pro všechny uživatele?"
${LangFileString} SecFileAssocTitle "Asociovat soubory"
${LangFileString} SecDesktopTitle "Ikonu na plochu"

${LangFileString} SecCoreDescription "Soubory VibeCADu."
#${LangFileString} SecAllUsersDescription "Instalovat VibeCAD pro všechny uživatele nebo pouze pro současného uživatele."
${LangFileString} SecFileAssocDescription "Soubory s příponou .FCStd se automaticky otevřou v VibeCADu."
${LangFileString} SecDesktopDescription "Ikonu VibeCADu na plochu."
#${LangFileString} SecDictionaries "Slovníky"
#${LangFileString} SecDictionariesDescription "Spell-checker dictionaries that can be downloaded and installed."

#${LangFileString} PathName 'Cesta k souboru $\"xxx.exe$\"'
#${LangFileString} InvalidFolder 'Soubor $\"xxx.exe$\" není v zadané cestě.'

#${LangFileString} DictionariesFailed 'Download of dictionary for language $\"$R3$\" failed.'

#${LangFileString} ConfigInfo "The following configuration of VibeCAD could take a while."

#${LangFileString} RunConfigureFailed "Nelze spustit konfigurační skript"
${LangFileString} InstallRunning "Instalátor je již spuštěn!"
${LangFileString} AlreadyInstalled "VibeCAD ${APP_SERIES_KEY2} je již nainstalován!$\r$\n\
				Installing over existing installations is not recommended if the installed version$\r$\n\
				is a test release or if you have problems with your existing VibeCAD installation.$\r$\n\
				In these cases better reinstall VibeCAD.$\r$\n\
				Dou you nevertheles want to install VibeCAD over the existing version?"
${LangFileString} NewerInstalled "You are trying to install an older version of VibeCAD than what you have installed.$\r$\n\
				  If you really want this, you must uninstall the existing VibeCAD $OldVersionNumber before."

#${LangFileString} FinishPageMessage "Blahopřejeme! VibeCAD byl úspěšně nainstalován.$\r$\n\
#					$\r$\n\
#					(První spuštění VibeCADu může trvat delší dobu.)"
${LangFileString} FinishPageRun "Spustit VibeCAD"

${LangFileString} UnNotInRegistryLabel "Nelze nalézt VibeCAD v registrech.$\r$\n\
					Zástupce na ploše a ve Start menu nebude smazán."
${LangFileString} UnInstallRunning "Nejprve musíte zavřít VibeCAD!"
${LangFileString} UnNotAdminLabel "Musíte mít administrátorská práva pro odinstalování VibeCADu!"
${LangFileString} UnReallyRemoveLabel "Chcete opravdu smazat VibeCAD a všechny jeho komponenty?"
${LangFileString} UnFreeCADPreferencesTitle 'Uživatelská nastavení VibeCADu'

#${LangFileString} SecUnProgDescription "Odinstalovat xxx."
${LangFileString} SecUnPreferencesDescription 'Smazat konfigurační adresář VibeCADu$\r$\n\
						$\"$AppPre\username\$\r$\n\
						$AppSuff\$\r$\n\
						${APP_DIR_USERDATA}$\")$\r$\n\
						pro všechny uživatele.'
${LangFileString} DialogUnPreferences 'You chose to delete the VibeCADs user configuration.$\r$\n\
						This will also delete all installed VibeCAD addons.$\r$\n\
						Do you agree with this?'
${LangFileString} SecUnProgramFilesDescription "Odinstalovat VibeCAD a všechny jeho komponenty."
