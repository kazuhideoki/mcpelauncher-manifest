# Joy-Conゲームパッド経路の切り分け（履歴）

これは標準採用前の調査記録。現在の標準版は[../README.md](../README.md)の`setup.sh`を使う。
以下のパッチとビルドスクリプトは、manifest `825ef10574681d82afc17884b8f11dfec196a2c1`時点の
初期化済みチェックアウト専用。固定依存はこのディレクトリの`source_lock.json`に保存した。
現在の標準game-windowへ古い診断パッチを重ねて適用しない。

`game-window-probe.patch`は、`source_lock.json`のgame-window
`841c716024a63bcf25a8007a2d26199887741c09`に適用する診断パッチ。
環境変数を指定しない通常起動では、既存のキーボード・マウス変換を使う。

| `MCPELAUNCHER_JOYCON_PROBE` | 動作 |
| --- | --- |
| `connect` | Appleが認識するJoy-Con (L/R)を1台として登録。ボタン・軸・キー・マウスの変換イベントは送らない |
| `neutral` | 登録に加え、LEFT_X=0の軸コールバックを毎フレーム呼ぶ。クライアントが作るMotionEventには他の軸の初期値0も含まれる |
| `buttons` | ボタンと十字キー。十字キーはクライアント側でMotionEventになる |
| `left` | buttonsに加え左スティック |
| `right` | leftに加え右スティック |
| `full` | rightに加えZL/ZR。通常の入力フィルターで操作確認する |

物理キーボード・マウスは引き続き使える。GLFWのゲームパッド登録は
実験中だけ無効にし、同じJoy-Conの重複登録と他のパッド入力を排除する。
`connect`では入力フィルターをGamepad Onlyに固定しない。
`neutral`でMotionEventを確実に試す場合は
`MCPELAUNCHER_CLIENT_RAW_INPUT=1`を併用する。
これは入力フィルターを無効にし、物理マウスでのメニュー操作とゼロ値イベントの比較を可能にする。
本来の自動切り替えとは条件が異なるため、フィルター有効時の試験と分けて記録する。

`MCPELAUNCHER_JOYCON_PROBE_GATE`にファイルの絶対パスを指定すると、
そのファイルが存在するときだけ登録する。未指定ならJoy-Con検出時に登録する。
メニュー到達後やワールド読み込み後の登録比較に使う。
フォーカスの変化だけでは接続・切断通知を繰り返さない。

## 再現方法

1. 依存ソースが取得済みの元リポジトリで`python3 joycon/manage.py verify`を実行する。
2. 別の非追跡ディレクトリへソースをコピーする。`.git`・`build`・`.local`は除外する。
3. コピー先game-windowで`game-window-probe.patch`、コピー先mcpelauncher-clientで
   `client-joystick-source.patch`を、それぞれ`patch -p1 < /absolute/path/to/patch`で適用する。
   修正前の比較を行う場合だけ、後者を適用しない。
4. `joycon/manage.py`のbuild関数と同じCMake設定でコピー先をビルドする。
   診断パッチを含むので、通常版の固定ソース検証を無理に通すためにロックを書き換えない。
5. 別のruntimeへ本体・ネイティブライブラリ・公式アプリへのリンクを配置する。
   1.26.51.1を指定し、実行更新Modは元の1つだけを参照する。
6. `-dd`で検証専用データを指定し、コピーしたオフラインワールドだけで比較する。
   認証・起動用データをローカルコピーした場合はruntime全体を非公開扱いにする。
7. 保存済み安定版を同じ検証用データで起動できることを先に確認する。
8. `connect`で起動し、`connect begin`と`connect returned`の両方を確認する。
   その後、物理マウスでコピーしたワールドを開く。

## 診断の注意

- `onGamepadState`が戻ったこととゲーム内部の接続通知完了は同義ではない。
  起動初期は`WindowCallbacks::startSendEvents`までJNI通知が遅延する。
- `connect`は軸を送らない。`neutral`はゼロ値、`left`・`right`・`full`は実入力を送る。
  現在のGameActivity経路では1軸のコールバックから
  全軸を含むMotionEventが構築される。
- 初期化前クラッシュ、更新ModのHTTP処理のクラッシュ、ワールド読み込み時の
  `libminecraftpe.so+0xaaf738c`は分けて記録する。
- 再接続の調査では既存`JniSupport::setGameControllerConnected`の切断分岐にも注意。
  現ソースは`else if(connected && removedMethod)`であり、falseの切断通知を送らない。
  これはコード上の別の不具合候補で、今回のワールド読み込みクラッシュの原因とは未確定。
- 切断時にボタン解放・軸のゼロ化を送る前にクライアント側の状態を破棄するため、
  上記の切断通知不備と合わせて、押下状態がゲーム側へ残る可能性がある。
- 物理マウスからJoy-Conへ切り替える直後のボタン入力は、クライアントの入力切替待ち時間に
  拒否されても診断側で送信済みとして記録される。押下・解放の取りこぼしがあり得るため、
  フォーカス喪失時も含めて通常版採用前に確認・修正する。
- 生ログ・認証データ・本体・ワールドはコミットしない。

## 2026-09-21の作業

- 元ソースの固定33サブモジュールの検証成功。
- 上記パッチを隔離コピーへ適用し、RelWithDebInfo / GLFWでビルド成功。
- 空に近い検証データでは実験版・保存済み安定版の両方が更新ModのHTTP応答処理付近でSIGSEGV。
  ゲームパッド登録固有の失敗とは扱わない。
- 普段の起動用データを検証先へコピー後、保存済み安定版で同じコピーを開けたとユーザーが確認。
- `connect`で`Gamepad connected #0`と`connect returned`を確認。ユーザーが同じコピーを開けることを確認。
- 修正前`neutral` + RAW_INPUTで起動直後にSIGSEGV。前回同様`libminecraftpe.so+0xaaf738c`を含むスタック。
- `client-joystick-source.patch`でGameActivityのMotionEvent.sourceだけをGAMEPADからJOYSTICKへ変更。
  修正版はゼロ値入力を送りながらメニュー表示に成功。
- ワールド読み込み後にゲートを開き、修正版のゼロ値入力でワールド内の描画を維持。
  LT/RT・十字キー・インベントリのゲームパッド操作ガイド表示を画面確認。保存して終了も確認。
- `full`を通常の入力フィルターで起動。ユーザーが「一通り操作できた・クラッシュなし」と確認。
  確認対象はボタンでのメニュー操作、コピーしたワールドの読み込み、左スティック移動、右スティック視点、ZL/ZR。
- 通常のJoy-Con-Keyboardプロファイル、本体、元ワールドは変更していない。
  実操作確認版は検証専用データを使用。LAN・長時間・再接続・再起動後の安定性は未確認。
- LLDBは初期化中にEXC_SYSCALLで停止する。継続処理を加えた実行では同じタイミングでクラッシュせず、実際のfault PCはまだ取得できていない。

イベント種別の根拠：[Android公式コントローラー入力](https://developer.android.com/games/sdk/game-controller/controller-input)。
GAMEPAD種別ではゼロ値イベントで以前と同じスタックを含むSIGSEGVを再現し、
JOYSTICK種別ではワールド内のゼロ値入力と実Joy-Con操作が成功した。
入力種別の不整合が今回のクラッシュに関与する強い証拠だが、内部のfault PCは未取得であり、
ゲームパッド経路全体の長期安定性を証明したものではない。

## 隔離ビルド用スクリプト

```sh
python3 joycon/experiments/build_probe.py \
  --source /path/to/initialized/mcpelauncher-manifest \
  --destination /path/to/NEW/diagnostic-build \
  --cached-deps /path/to/existing/build/joycon/_deps
```

`--cached-deps`は省略可能。省略時は元CMakeの固定依存を取得する。
スクリプトは取得済み元ソースの固定コミット検証を実行してから、別ディレクトリへコピーする。
本体とパッチのSHA-256を保存する。通常プロファイルの切り替えは行わない。
スクリプトの新規隔離ビルド結果と、独立レビューで見つかった修正点は
[REVIEW.md](REVIEW.md)に記録する。手動ビルド版の実操作確認と、スクリプトで再構築した本体の
実操作確認は分けて扱う。

## 今回の実操作確認版

非追跡runtime：`.local/gamepad-probe/`。
`start-gamepad.command`を実行すると、確認済みの`mcpelauncher_gamepad_v1`を
`full`モードで起動する。ゲームが既に起動している場合は保存して閉じてから実行する。
通常プロファイルの選択は変えず、検証用`data/`と`cache/`を使う。
このコピーのワールドで進めた内容は元ワールドへ反映されない。

診断パッチ、1行のイベント種別修正、実操作確認済み本体のSHA-256は
runtimeの`build-evidence.json`に保存。runtimeにはローカルの起動用データが含まれるため、
そのまま共有・コミットしない。

実験版はGLFWのゲームパッド登録を無効にし、左右一組のJoy-Conだけを扱う。
実製品用への反映時は、他のコントローラーとの共存、フォーカス喪失時の解放、
再接続通知、物理ボタン表記を追加確認する。
