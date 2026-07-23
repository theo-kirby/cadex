/*
VibeCAD Installer Language File
Language: Japanese
*/

!insertmacro LANGFILE_EXT "Japanese"

${LangFileString} TEXT_INSTALL_CURRENTUSER "(現ユーザー用に導入を行う)"

${LangFileString} TEXT_WELCOME "このウィザードが、あなたのVibeCAD導入作業中のご案内をします。$\r$\n\
				$\r$\n\
				$_CLICK"

#${LangFileString} TEXT_CONFIGURE_PYTHON "Pythonスクリプトをコンパイルしています..."

${LangFileString} TEXT_FINISH_DESKTOP "デスクトップにショートカットを作成する"
${LangFileString} TEXT_FINISH_WEBSITE "github.com/10-X-eng/vibecadを開いて最新ニュースやサポート、ヒントなどを入手する"

#${LangFileString} FileTypeTitle "VibeCAD文書"

#${LangFileString} SecAllUsersTitle "すべてのユーザー用に導入を行いますか？"
${LangFileString} SecFileAssocTitle "ファイル関連付け"
${LangFileString} SecDesktopTitle "デスクトップ・アイコン"

${LangFileString} SecCoreDescription "VibeCADのファイル。"
#${LangFileString} SecAllUsersDescription "VibeCADをすべてのユーザー用に導入するか、現在のユーザー向けだけに導入するか。"
${LangFileString} SecFileAssocDescription "拡張子が.FCStdのファイルは自動的にVibeCADで開かれる。"
${LangFileString} SecDesktopDescription "デスクトップ上のVibeCADアイコン"
#${LangFileString} SecDictionaries "辞書"
#${LangFileString} SecDictionariesDescription "ダウンロード及び導入が可能なスペルチェック用辞書"

#${LangFileString} PathName '$\"xxx.exe$\"ファイルへのパス'
#${LangFileString} InvalidFolder '指定されたパスに$\"xxx.exe$\"ファイルが見つかりません。'

#${LangFileString} DictionariesFailed '言語$\"$R3$\"用辞書のダウンロードに失敗しました。'

#${LangFileString} ConfigInfo "以下のVibeCADの設定には少々時間がかかります。"

#${LangFileString} RunConfigureFailed "configureスクリプトを実行することができませんでした"
${LangFileString} InstallRunning "導入プログラムは既に動作中です！"
${LangFileString} AlreadyInstalled "VibeCAD${APP_SERIES_KEY2}は既に導入済みです！$\r$\n\
				導入済みのバージョンがテスト版であったり、導入済みVibeCADで問題がある場合には、$\r$\n\
				上書き導入作業は推奨されません。これらの場合には、VibeCADを最初から再導入する$\r$\n\
				ことが推奨されます。$\r$\n\
				これらを承知の上で、既存のVibeCADを上書きしますか？"
${LangFileString} NewerInstalled "あなたは、既に導入済みのVibeCADよりも古い版を導入しようとしています。$\r$\n\
				  本当にそうしたいのであれば、既存の VibeCAD $OldVersionNumber をまず導入解除してください。"

#${LangFileString} FinishPageMessage "おめでとうございます！VibeCADが正しく導入されました。$\r$\n\
#					$\r$\n\
#					初回のVibeCADの起動には時間がかかります。）"
${LangFileString} FinishPageRun "VibeCADを起動する"

${LangFileString} UnNotInRegistryLabel "レジストリにVibeCADが見当たりません。$\r$\n\
					デスクトップとスタートメニューのショートカットは削除されません。"
${LangFileString} UnInstallRunning "まずVibeCADを閉じてください！"
${LangFileString} UnNotAdminLabel "VibeCADの導入解除を行うには、管理者権限を持っていなくてはなりません！"
${LangFileString} UnReallyRemoveLabel "本当に、VibeCADとすべての附属コンポーネントを削除してしまう積もりですか？"
${LangFileString} UnFreeCADPreferencesTitle 'VibeCADのユーザー設定'

#${LangFileString} SecUnProgDescription "文献管理プログラムxxxの導入解除を行います。"
${LangFileString} SecUnPreferencesDescription 'ユーザー共通のVibeCADの設定フォルダ$\r$\n\
						$\"$AppPre\username\$\r$\n\
						$AppSuff\$\r$\n\
						${APP_DIR_USERDATA}$\")$\r$\n\
						を削除します。'
${LangFileString} DialogUnPreferences 'You chose to delete the VibeCADs user configuration.$\r$\n\
						This will also delete all installed VibeCAD addons.$\r$\n\
						Do you agree with this?'
${LangFileString} SecUnProgramFilesDescription "VibeCADとすべての附属コンポーネントの導入解除を行います。"
