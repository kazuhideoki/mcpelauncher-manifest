# macOS Joy-Conゲームパッド版のセットアップ

2026-09-21に操作確認したネイティブゲームパッド入力を標準にする。
左スティックのアナログ移動、右スティックの視点、メニュー、ZL/ZRをゲームパッドとして扱う。

## ワンコマンド

このリポジトリの`main`で実行する。

```sh
./joycon/setup.sh
```

処理内容：

1. HomebrewのCMake・Python・OpenSSL・SDL3の不足分をインストール。
2. 未取得のサブモジュールを取得し、固定コミット・変更の有無を検証。
3. game-windowのネイティブ入力と、クライアントのJOYSTICKイベント種別修正を含めてビルド。
4. `~/Library/Application Support/mcpelauncher/joycon-gamepad/releases/`に本体と依存ライブラリを配置。
5. 設定をバックアップし、`Joy-Con-Gamepad`を追加または管理下の既存設定を更新して選択。

配置先はリポジトリや一時worktreeの外なので、ソースの作業場所を変えても本体は残る。
起動は通常のMinecraft Bedrock Launcherから「遊ぶ」。普段のワールド保存先を使う。
実験版の`Diagnostic - Offline Copy`で進めた内容を元ワールドへ自動で戻す処理はしない。
他のプロファイルは自動削除しない。旧Joy-Con-Keyboardのローカル配置は削除済み。

同じソース・設定で再実行できる。セットアップが管理しているプロファイルを手動で変更した場合は、
その変更を上書きせず停止する。復旧には表示されたバックアップを使う。
ゲームとランチャーは設定の切り替え前に保存して終了する。
起動中なら配置まで行い、プロファイル変更前に停止するため、終了後に同じコマンドを再実行する。

## 前提

- Apple SiliconのMac、Homebrew、XcodeまたはCommand Line Tools。
- `/Applications/Minecraft Bedrock Launcher.app`を導入済み。
- 購入済みMinecraft **1.26.51.1 / code 972605101 / arm64-v8a**をランチャーでダウンロード済み。
- 対応する更新Modが`mods/mcpelauncher-updates/1.26.45.1/arm64-v8a`に導入済み。

購入・ログイン・ゲーム本体や更新Modの取得はランチャーで行う。
コマンドはそれらを確認し、不足があれば必要な場所を表示して止まる。
実行Modは元の1つだけ参照し、別途作るバージョンメタデータに実行ファイルは含めない。

初回取得：

```sh
ghq get https://github.com/kazuhideoki/mcpelauncher-manifest.git
cd "$(ghq root)/github.com/kazuhideoki/mcpelauncher-manifest"
./joycon/setup.sh
```

既存checkoutが古い場合は、変更を確認してから`main`を更新する。
セットアップは変更済みソースをリセットしたり、上流の最新版へ自動更新したりしない。

## 個別設定・復元

```sh
./joycon/setup.sh --jobs 10
./joycon/setup.sh --stage-only
./joycon/setup.sh --launcher-app '/path/to/Minecraft Bedrock Launcher.app' \
  --data-dir '/path/to/mcpelauncher' --update-mod '/path/to/update-mod'
python3 joycon/manage.py restore --receipt '/path/printed/by/setup/receipt.json'
```

復元は追加後にプロファイル設定が変更されていない場合だけ実行する。
ワールドと認証ファイルはセットアップ・復元で編集しない。
Homebrewの依存と公式アプリは配置後も必要。アプリを移動したら新しいパスでセットアップし直す。

## ビルドと変更の所在

- `game-window`：fork本体にJoy-Con入力を実装。既定は`full`。
- `joycon/client_fix.cmake`：固定された上流クライアントのソースを変更せず、ビルド先に
  `window_callbacks.cpp`を生成し、MotionEventの種別だけをGAMEPADからJOYSTICKへ変更してコンパイル。
  想定した置換箇所が1つでなければ停止する。
- `source_lock.json`：固定した33サブモジュール。game-windowのgitlinkと同じコミットを記録する。
- `build/joycon-gamepad/joycon_build_report.json`：本体・修正処理のSHA-256、ソース固定情報、ビルド環境。
- `joycon-gamepad/setup-state.json`と各releaseの`profile_backups/`：管理対象と復元情報。

```sh
python3 joycon/manage.py verify
python3 joycon/manage.py build --jobs 10
python3 -m unittest discover -s joycon/tests -v
shellcheck joycon/setup.sh joycon/launch_client.sh
shfmt -d joycon/setup.sh joycon/launch_client.sh
```

macOSの大文字小文字を区別しないディスクでは、bionicのヘッダー8組が衝突する。
固定Git blobとの一致を確認できる場合だけ許容する。
Homebrew・Xcode・SDKは実環境を使うため、バイナリの完全一致は保証しない。
deployment target 11.0を指定しても、現在のHomebrewライブラリがmacOS 11で動くという意味ではない。

変更は自分のforkの`main`へPRを作成する。game-windowを先にマージし、manifestのgitlinkとロックを更新する。
この2つのforkで管理し、クライアントの上流checkoutを直接変更しない。

## 操作と既知の制約

**2026-09-21追記：最初からJoy-Conを有効にするとワールド読み込み中にクラッシュする問題は未解決。**
診断版では読み込み後の接続で操作できたが、標準版への修正は未反映。
再現条件・検証結果・実際の停止位置は[クラッシュ調査記録](experiments/WORLD_LOAD_CRASH.md)を参照。

基本操作はMinecraftのコントローラー設定に従う。ボタン表記・感度はゲーム内で設定する。
左右セットのJoy-Con (L/R)を1台として扱い、GLFW経由のゲームパッド登録は無効にして重複入力を避ける。
他のゲームパッドとの共存は未確認。

旧Joy-Con-Keyboardのプロファイル・専用起動スクリプト・実行ファイルは使用しない。
以前のDYLD挿入ライブラリは使用しない。

操作確認はメニュー、検証用ワールド読み込み、左右スティック、ZL/ZR。
長時間・再起動・LAN・再接続は未確認。切断時の解放と、マウスとの入力切替直後の
ボタン取りこぼしは既知の制約として残る。詳細は[独立レビュー](experiments/REVIEW.md)。
標準版への選択はユーザーの操作確認と指定に基づくもので、これらの未確認項目が解消したという意味ではない。

過去の移管記録は[VALIDATION.md](VALIDATION.md)、原因切り分けは[実験記録](experiments/README.md)。
本体・依存バイナリ・ワールド・認証情報・個人設定・生ログはコミットやpushをしない。
