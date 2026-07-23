/*
VibeCAD Installer Language File
Language: Swedish
*/

!insertmacro LANGFILE_EXT "Swedish"

${LangFileString} TEXT_INSTALL_CURRENTUSER "(Installerad för aktuell användare)"

${LangFileString} TEXT_WELCOME "Denna guide tar dig igenom installationen av $(^NameDA), $\r$\n\
				$\r$\n\
				$_CLICK"

#${LangFileString} TEXT_CONFIGURE_PYTHON "Kompilerar Pythonskript..."

${LangFileString} TEXT_FINISH_DESKTOP "Skapa skrivbordsgenväg"
${LangFileString} TEXT_FINISH_WEBSITE "Besök github.com/10-X-eng/vibecad för de senaste nyheterna, support och tips"

#${LangFileString} FileTypeTitle "VibeCAD-dokument"

#${LangFileString} SecAllUsersTitle "Installera för alla användare?"
${LangFileString} SecFileAssocTitle "Filassociationer"
${LangFileString} SecDesktopTitle "Skrivbordsikon"

${LangFileString} SecCoreDescription "VibeCAD-filerna."
#${LangFileString} SecAllUsersDescription "Installera VibeCAD för alla användare, eller enbart för den aktuella användaren."
${LangFileString} SecFileAssocDescription "Filer med ändelsen .FCStd kommer att automatiskt öppnas i VibeCAD."
${LangFileString} SecDesktopDescription "En VibeCAD-ikon på skrivbordet."
#${LangFileString} SecDictionaries "Ordböcker"
#${LangFileString} SecDictionariesDescription "Stavningskontrollens ordböcker som kan laddas ned och installeras."

#${LangFileString} PathName 'Sökväg till filen $\"xxx.exe$\"'
#${LangFileString} InvalidFolder 'Filen $\"xxx.exe$\" finns inte i den angivna sökvägen.'

#${LangFileString} DictionariesFailed 'Nedladdning av ordbok för språk $\"$R3$\" misslyckades.'

#${LangFileString} ConfigInfo "Följande konfigurering av VibeCAD kommer att ta en stund."

#${LangFileString} RunConfigureFailed "Kunde inte köra konfigurationsskriptet"
${LangFileString} InstallRunning "Installationsprogrammet körs redan!"
${LangFileString} AlreadyInstalled "VibeCAD ${APP_SERIES_KEY2} är redan installerad!$\r$\n\
				Att installera över en nuvarande installation är inte rekommenderat om den installerade$\r$\n\
				versionen är en testutgåva eller om du har problem med din nuvarande VibeCAD-installation.$\r$\n\
				I dessa fall är det bättre att ominstallera VibeCAD.$\r$\n\
				Vill du ändå installera VibeCAD över den nuvarande versionen?"
${LangFileString} NewerInstalled "Du försöker att installera en äldre version av VibeCAD än vad du har installerad.$\r$\n\
				  Om du verkligen vill detta måste du avinstallera den befintliga VibeCAD $OldVersionNumber innan."

#${LangFileString} FinishPageMessage "Gratulerar! VibeCAD har installerats framgångsrikt.$\r$\n\
#					$\r$\n\
#					(Den första starten av VibeCAD kan ta en stund.)"
${LangFileString} FinishPageRun "Kör VibeCAD"

${LangFileString} UnNotInRegistryLabel "Kan inte hitta VibeCAD i registret.$\r$\n\
					Genvägar på skrivbordet och i startmenyn kommer inte att tas bort."
${LangFileString} UnInstallRunning "Du måste stänga VibeCAD först!"
${LangFileString} UnNotAdminLabel "Du måste ha administratörsbehörighet för att avinstallera VibeCAD!"
${LangFileString} UnReallyRemoveLabel "Är du säker på att du verkligen vill fullständigt ta bort VibeCAD och alla dess komponenter?"
${LangFileString} UnFreeCADPreferencesTitle 'VibeCAD-användarinställningar'

#${LangFileString} SecUnProgDescription "Avinstallerar xxx."
${LangFileString} SecUnPreferencesDescription 'Raderar VibeCAD-konfiguration$\r$\n\
						(katalog $\"$AppPre\username\$\r$\n\
						$AppSuff\$\r$\n\
						${APP_DIR_USERDATA}$\")$\r$\n\
						för dig eller för alla användare (om du är admin).'
${LangFileString} DialogUnPreferences 'You chose to delete the VibeCADs user configuration.$\r$\n\
						This will also delete all installed VibeCAD addons.$\r$\n\
						Do you agree with this?'
${LangFileString} SecUnProgramFilesDescription "Avinstallera VibeCAD och alla dess komponenter."
