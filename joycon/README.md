# macOS Joy-Con動作版の管理と再構築

このforkは、2026-09-20に動作確認したキーボード・マウス変換版v2を保存する。
管理ブランチは`main`。公式の最新版へ一括更新せず、`source_lock.json`のコミットを使う。

- Minecraft：1.26.51.1 / code 972605101 / arm64-v8a
- 普段使う既存プロファイル：Joy-Con-Keyboard
- macOSのJoy-Con (L/R)を、ゲーム内のキーボード・マウス処理へ変換する。
- 最終版のLAN同時プレイ、長時間動作、再起動後と再接続時の安定性は未確認。

## 取得

```sh
ghq get https://github.com/kazuhideoki/mcpelauncher-manifest.git
cd "$(ghq root)/github.com/kazuhideoki/mcpelauncher-manifest"
git switch main
git submodule sync --recursive
git submodule update --init --recursive
python3 joycon/manage.py verify
```

game-windowを直接改善する場合は、`kazuhideoki/game-window`もghq配下へ取得する。
両forkの`origin`は自分のfork、`upstream`は対応する`minecraft-linux`リポジトリとする。
PRは自分のforkの`main`へ作り、game-windowを先にマージする。
その後、manifestのgitlinkと`source_lock.json`を同じgame-windowコミットへ更新する。

## ビルド

必要なものはApple SiliconのMac、Xcode Command Line ToolsまたはXcode、Git、CMake、Python 3、Homebrewのopenssl@3とsdl3。
必要に応じて`brew install cmake openssl@3 sdl3`で用意する。

```sh
python3 joycon/manage.py build --jobs 10
```

出力は`build/joycon/mcpelauncher-client/mcpelauncher-client`。
環境・コミット・本体のSHA-256は、非追跡ファイル`build/joycon/joycon_build_report.json`に記録する。
`--build-dir`、`--openssl-root`、`--sdl3-dir`で環境固有のパスを指定できる。

元の記録と同じGLFW、RelWithDebInfo、macOS deployment target 11.0を使う。
`ENABLE_DEV_PATHS`だけはOFFにして、ビルド元の一時ディレクトリへ依存するフォールバックを除く。
実行に必要なネイティブライブラリは、配置時に本体の隣へコピーする。

依存ソースのコミットは固定する。Homebrewのライブラリ、Xcode、macOS SDKは実環境を利用するため、バイナリの完全一致を保証しない。
現在のHomebrewバイナリはmacOS 26向けであり、deployment target 11.0を指定してもmacOS 11で動くという意味ではない。
GLFWの取得URLは元のCMakeでコミット固定されている。初回はネットワーク接続が必要。

macOSの大文字小文字を区別しないディスクでは、bionicのLinuxヘッダー8組が衝突する。
検証スクリプトは、衝突先の内容が同じコミット内の対応するGit blobと一致する場合だけ許容する。
その他の追跡ファイルの変更と、コミットのずれは検証で拒否する。

## 別の場所へ配置する

以下の変数は自分の環境に合わせる。`runtime`は**存在しない新しいディレクトリ**にする。
この操作は既存のランチャー設定・認証情報・ワールドを書き換えない。

```sh
launcher_app='/Applications/Minecraft Bedrock Launcher.app'
data_dir="$HOME/Library/Application Support/mcpelauncher"
update_mod="$data_dir/mods/mcpelauncher-updates/1.26.45.1/arm64-v8a"
runtime="$PWD/.local/joycon_candidate"
python3 joycon/manage.py package \
  --destination "$runtime" \
  --launcher-app "$launcher_app" \
  --data-dir "$data_dir" \
  --update-mod "$update_mod"
```

`package`は以下を作成する。

- ビルドした本体、起動スクリプト、ネイティブ補助ライブラリ。
- 公式ランチャーのFrameworks・Resources・補助アプリへのリンク。
- 対応情報だけの`version_metadata/mod.json`。
- 個人のパスを埋めた非公開の`profile.fragment.ini`とチェックサム。
- ビルド情報とライセンス表記。

ゲーム本体、ワールド、認証情報、更新Modの実行ファイルはコピーしない。
更新Modは指定した元ディレクトリの1つだけを参照する。
公式ランチャーを移動・削除した場合は、リンク先を再設定して配置し直す。
生成された実行環境は`.local/`等の非追跡領域へ置き、配布物としてpushしない。

## 普段の環境への切り替えと復元

**今回はビルド・別配置までを検証し、既存環境への切り替えは実施していない。**
切り替えるときはMinecraftを保存して終了し、ゲーム本体とランチャーの両方を閉じる。
既存のJoy-Con-Keyboardを上書きせず、新しいプロファイルを追加する。

```sh
python3 joycon/manage.py activate \
  --runtime "$runtime" \
  --profiles-file "$data_dir/profiles/profiles.ini" \
  --name Joy-Con-Keyboard-Rebuilt
```

同じ名前のプロファイルがある場合は拒否する。
元の設定のバックアップと`receipt.json`をruntime内の`profile_backups/`へ保存する。
表示されたreceiptを指定すれば、元の選択と設定へ戻せる。

```sh
python3 joycon/manage.py restore --receipt '/path/to/profile_backups/activation_xxx/receipt.json'
```

復元は、追加後にプロファイル設定が変更されていない場合だけ実行する。
途中で別の変更をした場合は上書きせず停止する。バックアップとの差分を手動で確認する。
ワールドと認証情報は、追加・復元のどちらでも編集しない。

## 操作配置

| 入力 | 操作 |
| --- | --- |
| 左スティック | WASD移動。歩行速度はデジタル |
| 右スティック | 視点1300入力ピクセル/秒、メニューのカーソル650 |
| 十字キー上・左・右・下 | 視点切替・エモート・チャット・アイテムを落とす |
| メニュー中の十字キー | 矢印キー |
| ZR / ZL | 攻撃・破壊 / 使用・設置 |
| L / R | 前 / 次の持ち物 |
| ＋ / − | Escape / Tab |
| 左スティック押し込み | Ctrlでダッシュ |

Appleの論理Aはジャンプ／メニュークリック、Bはしゃがみ／戻る、Xはインベントリ、Yはアイテムを落とす。
Nintendoの物理ボタン表記との対応は別途確認が必要。
視点移動の端数を蓄積する。デッドゾーン0.15、移動のしきい値0.25、フレーム時間の上限50ms。
ゲーム側のマウス感度も視点速度へ影響する。

## 調査経緯と禁止する退行

1. macOSは左右のJoy-Conを認識したが、元のゲームパッド経路では操作できなかった。
2. DYLDで補助ライブラリを挿入する試作は、再起動後の停止を繰り返した。採用しない。
3. Apple入力をAndroidゲームパッドとして登録する試作は、一時的に動いたがワールドを開くと落ちた。
4. LAN参加の試行後にも問題が起きた。オフラインコピーでも同じSIGSEGVを再現し、通信だけが原因とはいえなかった。
5. 同じワールドを改造前の本体では開けた。キーボード・マウス変換版でも開けて操作できた。
6. v2で視点速度と十字キーを調整し、操作確認を得た。内部の正確なクラッシュ原因は未特定。
7. 別件として、更新Modを2つ読み込んだ構成では初期化が停止した。現在は対応情報のみと実行Mod1つを使う。

起動時の対応バージョン判定が古い場合は、バージョンコード固定と専用メタデータを確認する。
「Activate」という案内だけを根拠に、更新Modを重ねて有効化しない。
生ログには認証情報や識別子を含む場合があるため、コミット・pushしない。

## 検証と今後の改善

```sh
python3 -m unittest discover -s joycon/tests -v
shellcheck joycon/launch_client.sh
shfmt -d joycon/launch_client.sh
python3 joycon/manage.py verify
```

テストは一時ディレクトリで実行し、実際のプロファイルを編集しない。
ソース移管時のビルド・配置結果は[VALIDATION.md](VALIDATION.md)を参照。
今後はgame-windowで変更し、manifestの参照コミットを更新してビルドする。
入力改善と実機確認は小さく分け、動作版とワールドを残す。

元のライセンスは各リポジトリ・サブモジュール内に保持する。
Minecraft本体、認証情報、ワールド、生ログ、個人設定、依存ライブラリのバイナリはこのforkへ追加しない。
