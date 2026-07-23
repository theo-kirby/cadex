/*
VibeCAD Installer Language File
Language: Danish
*/

!insertmacro LANGFILE_EXT "Danish"

${LangFileString} TEXT_INSTALL_CURRENTUSER "(Installed for Current User)"

${LangFileString} TEXT_WELCOME "Denne guide vil installere VibeCAD på din computer.$\r$\n\
				$\r$\n\
				$_CLICK"

#${LangFileString} TEXT_CONFIGURE_PYTHON "Compiling Python scripts..."

${LangFileString} TEXT_FINISH_DESKTOP "Create desktop shortcut"
${LangFileString} TEXT_FINISH_WEBSITE "Visit github.com/10-X-eng/vibecad for the latest news, support and tips"

#${LangFileString} FileTypeTitle "VibeCAD-Dokument"

#${LangFileString} SecAllUsersTitle "Installer til alle brugere?"
${LangFileString} SecFileAssocTitle "Fil-associationer"
${LangFileString} SecDesktopTitle "Skrivebordsikon"

${LangFileString} SecCoreDescription "Filerne til VibeCAD."
#${LangFileString} SecAllUsersDescription "Installer VibeCAD til alle brugere, eller kun den aktuelle bruger."
${LangFileString} SecFileAssocDescription "Opret association mellem VibeCAD og .FCStd filer."
${LangFileString} SecDesktopDescription "Et VibeCAD ikon på skrivebordet"
#${LangFileString} SecDictionaries "Ordbøger"
#${LangFileString} SecDictionariesDescription "Spell-checker dictionaries that can be downloaded and installed."

#${LangFileString} PathName 'Sti til filen $\"xxx.exe$\"'
#${LangFileString} InvalidFolder 'Kunne ikke finde $\"xxx.exe$\".'

#${LangFileString} DictionariesFailed 'Download of dictionary for language $\"$R3$\" failed.'

#${LangFileString} ConfigInfo "Den følgende konfiguration af VibeCAD vil tage et stykke tid."

#${LangFileString} RunConfigureFailed "Mislykket forsog på at afvikle konfigurations-scriptet"
${LangFileString} InstallRunning "Installationsprogrammet kører allerede!"
${LangFileString} AlreadyInstalled "VibeCAD ${APP_SERIES_KEY2} er allerede installeret!$\r$\n\
				Installing over existing installations is not recommended if the installed version$\r$\n\
				is a test release or if you have problems with your existing VibeCAD installation.$\r$\n\
				In these cases better reinstall VibeCAD.$\r$\n\
				Dou you nevertheles want to install VibeCAD over the existing version?"
${LangFileString} NewerInstalled "You are trying to install an older version of VibeCAD than what you have installed.$\r$\n\
				  If you really want this, you must uninstall the existing VibeCAD $OldVersionNumber before."

#${LangFileString} FinishPageMessage "Tillykke!! VibeCAD er installeret.$\r$\n\
#					$\r$\n\
#					(Når VibeCAD startes første gang, kan det tage noget tid.)"
${LangFileString} FinishPageRun "Start VibeCAD"

${LangFileString} UnNotInRegistryLabel "Kunne ikke finde VibeCAD i registreringsdatabsen.$\r$\n\
					Genvejene på skrivebordet og i Start-menuen bliver ikke fjernet"
${LangFileString} UnInstallRunning "Du ma afslutte VibeCAD forst!"
${LangFileString} UnNotAdminLabel "Du skal have administrator-rettigheder for at afinstallere VibeCAD!"
${LangFileString} UnReallyRemoveLabel "Er du sikker på, at du vil slette VibeCAD og alle tilhørende komponenter?"
${LangFileString} UnFreeCADPreferencesTitle 'VibeCAD$\'s user preferences'

#${LangFileString} SecUnProgDescription 'Afinstallerer programmet $\"xxx$\".'
${LangFileString} SecUnPreferencesDescription 'Sletter VibeCAD$\'s konfigurations mappe$\r$\n\
						$\"$AppPre\username\$\r$\n\
						$AppSuff\$\r$\n\
						${APP_DIR_USERDATA}$\")$\r$\n\
						for alle brugere.'
${LangFileString} DialogUnPreferences 'You chose to delete the VibeCADs user configuration.$\r$\n\
						This will also delete all installed VibeCAD addons.$\r$\n\
						Do you agree with this?'
${LangFileString} SecUnProgramFilesDescription "Afinstallerer VibeCAD og alle dets komponenter."
