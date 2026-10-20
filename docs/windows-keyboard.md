# Windows のキー設定

常駐アプリを追加せず、左 Win キーを左 Alt キーとして使う。
共通設定は [`src/.config/dotfiles/windows-keyboard.json`](../src/.config/dotfiles/windows-keyboard.json)、
適用・解除は [`bin/setup-windows-keyboard.ps1`](../bin/setup-windows-keyboard.ps1) で管理する。
通常の Windows / WSL セットアップや `u` からは実行せず、必要な端末で明示的に適用する。

## 変更内容

| 物理的に押すキー | 適用後の操作 |
| --- | --- |
| 左 Win + Tab | Alt + Tab と同じウィンドウ切り替え。左 Win を押したまま Tab で選び、離して確定 |
| 左 Win + Shift + Tab | ウィンドウを逆順に選択 |
| 左 Win 単独 | 左 Alt として動作 |
| PrtSc / Print Screen | Snipping Tool でスクリーンショットの範囲を選択 |

左 Win の変更は、Windows の
[`Scancode Map`](https://learn.microsoft.com/en-us/previous-versions/windows/hardware/hid/keyboard-and-mouse-class-drivers#scan-code-mapper-for-keyboards)
を使う。これはキー自体の置き換えなので、左 Win を使った他のショートカットも Alt の組み合わせになる。
設定は端末の全ユーザー・接続された全キーボードに適用され、反映・解除には Windows の再起動が必要。
右 Win キーがある場合は、右側から通常の Win ショートカットを使える。

Print Screen の画面切り取り設定は、実行した Windows ユーザーにだけ適用する。
手動で変更する場合は「設定 → アクセシビリティ → キーボード → Print Screen キーを使用して画面キャプチャを開く」を使う。
キーボードによっては PrtSc と Fn の併用が必要。
PrtSc を使えない場合は、[Snipping Tool をタスクバーにピン留め](https://support.microsoft.com/ja-jp/windows/apps/use-snipping-tool-to-capture-screenshots)して起動できる。

## 適用と解除

Windows からアクセスできる dotfiles のパスを指定する。
WSL の clone を使う例では、ディストリビューション名と Linux ユーザー名を置き換える。

```powershell
$repo = '\\wsl$\Ubuntu\home\<Linuxユーザー名>\git\dotfiles'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$repo\bin\setup-windows-keyboard.ps1" -WhatIf
```

`-WhatIf` は管理者権限なしで確認でき、設定やバックアップを書き込まない。
適用時だけ、**同じ Windows アカウントで管理者として PowerShell を開き**、パスを再設定して実行する。
別の管理者アカウントを使うと、Print Screen の設定とバックアップの所有者が変わる。

```powershell
$repo = '\\wsl$\Ubuntu\home\<Linuxユーザー名>\git\dotfiles'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$repo\bin\setup-windows-keyboard.ps1"
```

成功後、作業中のファイルを保存して Windows を手動で再起動する。
スクリプトは自動で再起動しない。再起動後はウィンドウの順送り・逆送り・キーを離したときの確定と、PrtSc の範囲選択を確認する。

初回の変更前に `%LOCALAPPDATA%\dotfiles\windows-keyboard.backup.json` へ元の設定を保存する。
再実行ではこのバックアップを置き換えず、同じ設定への書き込みを省く。
既存の異なる Scancode Map がある場合は、どちらの設定も変更せず停止する。
途中で失敗した場合もバックアップを残すので、原因を解消して再実行するか解除する。

解除は、適用した Windows アカウントの管理者 PowerShell から実行する。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$repo\bin\setup-windows-keyboard.ps1" -Restore
```

元の設定値、または元々値がなかった状態へ戻して確認した後、バックアップを削除する。
解除後も手動で再起動する。適用後に他のツールで変更された値がある場合は、上書きせず停止する。
バックアップは Git 管理に加えない。共通プロファイルを変更するときは、先に既存の設定を解除する。

## Win キーの主な用途

左 Win を Alt に変更すると、以下の操作には右 Win キーや別の起動方法が必要になる。
スタートメニューは Ctrl + Esc でも開ける。

| キー | 操作 |
| --- | --- |
| Win 単独 | スタートメニュー |
| Win + 矢印 / Win + Z | ウィンドウ整列 / スナップレイアウト |
| Win + L | 画面ロック |
| Win + V | クリップボード履歴（有効化が必要） |
| Win + E / Win + R | エクスプローラー / ファイル名を指定して実行 |
| Win + D / Win + I | デスクトップの表示・復帰 / 設定 |
| Win + Space / Win + . | 入力言語の切り替え / 絵文字パネル |
| Win + Ctrl + 左右 | 仮想デスクトップの切り替え |

[Microsoft のショートカット一覧](https://support.microsoft.com/ja-jp/accessibility/windows/keyboard-shortcuts-in-windows)も参照する。

## Copilot キーを右 Alt や Fn にしたい場合

Copilot キーは一般に左 Shift + Win + F23 などの組み合わせを送るため、
Scancode Map による単独キーの置き換えでは右 Alt にできない。
F23 だけを右 Alt に変更しても、同時に送られた Win や Shift が残る。
左 Win の置き換えによって Copilot キーの組み合わせも変わる可能性がある。
このプロファイルでは Copilot キーを別のキーとして使う設定を加えない。

右 Alt が必要になった場合は、先にこのプロファイルを解除して再起動し、
PowerToys の Keyboard Manager など、組み合わせを変更できる常駐ツールへ設定をまとめる。
PowerToys では「ショートカットの再マッピング」で実際に Copilot キーを押して入力を選び、送信先を Alt (Right) にする。
左 Win から左 Alt への変更も同じツールで設定し、押しっぱなし・他のキーとの併用・離した後の動作を確認する。
詳細は [Keyboard Manager の公式手順](https://learn.microsoft.com/ja-jp/windows/powertoys/keyboard-manager)を参照する。

Fn は通常キーボード本体やファームウェアが処理し、Windows に単独キーとして届かないため、
Scancode Map や一般的なキー変更ツールで Copilot キーから Fn に割り当てることはできない。
メーカーの BIOS や専用設定が対応している場合は、その機種の手順を使う。

Windows 標準の Copilot キー設定は、対応した環境で右 Ctrl やコンテキストメニューを選べる場合があるが、
Alt や Fn への割り当てとは異なる。
[Microsoft の Copilot キー設定の説明](https://support.microsoft.com/en-us/accessibility/windows/copilot/understand-updates-to-the-copilot-key-on-windows-devices)に従い、表示される選択肢を確認する。
