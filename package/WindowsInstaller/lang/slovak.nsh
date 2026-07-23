/*
VibeCAD Installer Language File
Language: Slovak
*/

!insertmacro LANGFILE_EXT "Slovak"

${LangFileString} TEXT_INSTALL_CURRENTUSER "(Inštalované pre súčasného užívateľa)"

${LangFileString} TEXT_WELCOME "Tento sprievodca Vám pomáha inštalovať VibeCAD.$\r$\n\
				$\r$\n\
				$_CLICK"

#${LangFileString} TEXT_CONFIGURE_PYTHON "Kompilácia Python skriptov..."

${LangFileString} TEXT_FINISH_DESKTOP "Vytvoriť skratku pre pracovnú plochu"
${LangFileString} TEXT_FINISH_WEBSITE "Navštívte github.com/10-X-eng/vibecad pre posledné novinky, podporu a tipy"

#${LangFileString} FileTypeTitle "VibeCAD dokument"

#${LangFileString} SecAllUsersTitle "Inštalovať pre všetkých užívateľov?"
${LangFileString} SecFileAssocTitle "Asociácie súborov"
${LangFileString} SecDesktopTitle "Ikona pracovnej plochy"

${LangFileString} SecCoreDescription "Súbory VibeCADu."
#${LangFileString} SecAllUsersDescription "Inštalovať VibeCAD pre všetkých užívateľov alebo len pre súčasného užívateľa."
${LangFileString} SecFileAssocDescription "Súbory s rozšírením .FCStd sa automaticky otvárajú v VibeCADe."
${LangFileString} SecDesktopDescription "Ikona VibeCADa na pracovnej ploche."
#${LangFileString} SecDictionaries "Slovníky"
#${LangFileString} SecDictionariesDescription "Slovníky pre kontrolu pravopisu ktoré možno načítať a inštalovať."

#${LangFileString} PathName 'Cesta na súbor $\"xxx.exe$\"'
#${LangFileString} InvalidFolder 'Súbor $\"xxx.exe$\" nie je na špecifikovanej ceste.'

#${LangFileString} DictionariesFailed 'Načítanie slovníka pre jazyk $\"$R3$\" zlyhalo.'

#${LangFileString} ConfigInfo "Nasledujúca konfigurácia VibeCADu trochu potrvá."

#${LangFileString} RunConfigureFailed "Nedal sa spustiť konfiguračný skript"
${LangFileString} InstallRunning "Inštalačný program už beží!"
${LangFileString} AlreadyInstalled "VibeCAD ${APP_SERIES_KEY2} je už inštalovaný!$\r$\n\
				Inštalovať ponad existujúce inštalácie sa nedoporučuje keď inštalovaná verzia$\r$\n\
				je testovné vydanie alebo keď máte problémy s existujúcou inštaláciou.$\r$\n\
				V takýchto prípadoch je lepšie reinštalovať VibeCAD.$\r$\n\
				Napriek tomu chcete inštalovať VibeCAD ponad existujúcu verziu?"
${LangFileString} NewerInstalled "Pokúšate sa inštalovať verziu VibeCADu ktorá je staršia ako tá ktorá je inštalovaná.$\r$\n\
				  Keď to naozaj chcete, odinštalujte najprv existujúci VibeCAD $OldVersionNumber."

#${LangFileString} FinishPageMessage "Gratulácia! VibeCAD bol úspešne inštalovaný.$\r$\n\
#					$\r$\n\
#					(Prvý VibeCAD štart môže trvať niekoľko sekúnd.)"
${LangFileString} FinishPageRun "Spustiť VibeCAD"

${LangFileString} UnNotInRegistryLabel "Nemôžem nájsť VibeCAD v registre.$\r$\n\
					Skratky na pracovnej ploche a v štartovacom Menu sa nedajú odstrániť."
${LangFileString} UnInstallRunning "Najprv treba zavrieť VibeCAD!"
${LangFileString} UnNotAdminLabel "Pre odinštaláciu VibeCAD potrebujete administrátorské práva!"
${LangFileString} UnReallyRemoveLabel "Ste si istý, že chcete kompletne odinštalovať VibeCAD a všetky jeho súčiastky?"
${LangFileString} UnFreeCADPreferencesTitle 'VibeCADove užívateľské nastavenia'

#${LangFileString} SecUnProgDescription "Odinštaluje xxx."
${LangFileString} SecUnPreferencesDescription 'Odstráni konfiguračný adresár VibeCADu $\r$\n\
						$\"$AppPre\username\$\r$\n\
						$AppSuff\$\r$\n\
						${APP_DIR_USERDATA}$\")$\r$\n\
						pre všetkých užívateľov (keď máte administrátorské práva).'
${LangFileString} DialogUnPreferences 'You chose to delete the VibeCADs user configuration.$\r$\n\
						This will also delete all installed VibeCAD addons.$\r$\n\
						Do you agree with this?'
${LangFileString} SecUnProgramFilesDescription "Odinštaluj VibeCAD a všetky jeho súčiastky."
