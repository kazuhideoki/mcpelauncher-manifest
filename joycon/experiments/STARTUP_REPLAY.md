# 起動時入力の再現試験（2026-09-21 追記）

**原因未特定。直近の通常版の実機試験では再現せず、修正は導入していない。**
実機のJoy-Conが切断されていたため、入力経路に診断用の状態ファイルを追加して比較した。
合成入力の成功を、実機の安定動作やクラッシュ修正の証拠として扱わない。

## 確認したこと

- GameActivityMotionEventのサイズ（1760 bytes）、historySizeと履歴ポインタの位置は、
  このゲームのARM64コードと一致した。構造体サイズの単純な不一致は確認できなかった。
- 以前のfault PC `0xab1db78`の呼び出し元`0xaaf72fc`は、RTTIとvtableから
  `PersonaMinecraftGraphicsProvider`のメソッドと特定した。
  処理は画像IDに対応する要素を検索・解放する経路で、スティック処理そのものではない。
- 同オブジェクトは16 bytesで、`+8`に描画オブジェクトへのポインタを保持する。
  コンストラクタは`0xaaf6f60`、vtable address pointは`0x12d0b7c8`。
  呼び出し元は保持ポインタに`0x78`を加えてfault位置の検索処理へ渡す。
- 成功試行では生成時のポインタは正常だった。生成直後またはメニューで設定した
  ハードウェア監視点では、そのフィールドの書き換えを観測していない。
  これは失敗試行の解放後使用や破壊を否定する証拠ではない。
- コピーしたワールドで、ゲームパッド入力だけによる一覧操作・読み込みが成功した。
  デバッガーなし、入力モードを起動時からGamepadに固定した試行、
  `MallocScribble=1`と生成・解放追跡を組み合わせた試行でも読み込みは成功した。
  これらは異なる診断条件の試行であり、同一条件の反復安定性試験ではない。
- マウスを使うと入力モードが切り替わるため、マウスでワールドを選んだ試行を
  「ゲームパッド入力だけでの読み込み成功」に含めない。
- 通常と異なる`-dd`での試行は、更新ModのHTTP完了処理で起動中に別のクラッシュ
  （pthread_mutex_lockへの引数`0x80`）を起こした。元の読み込み時クラッシュと混同しない。
- 更新Modを外した比較は`pthread_sigmask`未解決でゲーム起動に至らなかった。
  更新Modを原因と断定したり、削除を回避策にしたりする根拠は得られていない。

別件として、固定clientの`JniSupport::setGameControllerConnected`は切断側の条件にも
`connected`を使っており、切断通知が送られない。native側の切断時にも押下・軸の解放が
不足している。再接続対応では修正が必要だが、今回のfaultの原因とする証拠はない。

## 診断差分

[startup-replay.patch](startup-replay.patch)を、既存の
[crash-context.patch](crash-context.patch)適用済みの隔離ソースに追加する。
通常のsetup、プロファイル、releaseには組み込まない。

- `MCPELAUNCHER_DIAGNOSTIC_PAD_FILE`：接続状態、6軸、15ボタンの計22数値を読む。
  未指定なら通常どおりGameControllerを読む。ファイルは一時ファイルからrenameで更新する。
  接続状態以外の入力には通常と同じウィンドウのフォーカス条件が適用される。
- 軸順：LEFT_X、LEFT_Y、RIGHT_X、RIGHT_Y、LEFT_TRIGGER、RIGHT_TRIGGER。
- ボタン順：A、B、X、Y、LB、RB、BACK、START、GUIDE、LEFT_STICK、RIGHT_STICK、
  DPAD_UP、DPAD_RIGHT、DPAD_DOWN、DPAD_LEFT。
- `MCPELAUNCHER_DIAGNOSTIC_PERSONA=1`：当該ARM64版のコンストラクタ命令を照合して、
  生成時のポインタと削除時のポインタを記録する。画像解放時には生成時の値と比較する。
  ゲームコードを書き換える診断なので、それ自体がタイミング等に影響し得る。
  この追跡は失敗時の証拠取得用であり、ポインタを補正する修正ではない。

ポインタ追跡ではmacOSのJIT書き込み切替を使用した。
初期のmprotect方式はPermission deniedで失敗し、追跡は動作していなかった。
その初期試行を追跡成功に含めない。

## ローカル証拠と再開地点

非追跡の`.local/startup-investigation-20260921/`に、起動・入力・LLDBスクリプト、
ログ、チェックサムを保存した。生ログは認証関連情報等を含み得るため共有しない。
診断用アプリは`/private/tmp/joycon-startup-fix/JoyCon Diagnostic.app`。
ビルド元は既存の`/private/tmp/joycon-trigger-investigation/source`、ビルド先は同`build`。
一時領域の永続性は保証しない。

試験用ワールドは`Diagnostic - Controller Startup`。
通常データ内の`codex_startup_diagnostic_20260921`に配置したコピーを使う。
ワールド名のキャッシュにより一覧の名前と順序が変わるため、操作前に対象を確認する。
元ワールドのファイルには本調査中の起動・保存時刻も残っており、
「一切変更されていない」とは断定しない。調査開始時のコピーは一時領域に保持した。

以下の実機比較を実施した。今後再発した場合は、成功時との差とfault contextを比較する。
成功試行だけから登録遅延やポインタ補正を製品に導入しない。

## 実機での再試験 1

左右Joy-ConのBluetooth接続を確認してから、合成入力・入力モード固定・MallocScribbleを
使わずに診断版を起動した。生成・解放追跡のみ有効。ユーザーから、ワールド読み込みと
操作が成功したとの報告を得た。ログにも左右トリガーの0→1→0が記録され、
採取時点でfault context・ポインタ不一致・削除通知はなかった。
この試行では描画オブジェクト生成後にコントローラーの接続通知が出ている。
生成より先に通知される合成入力試行も成功しており、この順序だけを原因としない。

生ログ：`.local/startup-investigation-20260921/physical-startup-1.log`。
次は生成・解放追跡を無効にし、診断用コード書き換えの影響を切り分ける。

## 実機での再試験 2

生成・解放追跡も無効にして再起動した試行で、ユーザーから同じ操作の成功報告を得た。
ログに左右トリガーの0→1→0があり、fault contextはなかった。
生ログ：`.local/startup-investigation-20260921/physical-startup-2-uninstrumented.log`。
この本体には未使用の診断コードとfault contextの記録機能は残っている。

通常版と診断版のCMake設定（RelWithDebInfo、C++オプション、JNIVM設定、macOS deployment target）
に比較した範囲で差はなかった。一方、通常releaseにはContents/Info.plistがなく、
診断用アプリにはInfo.plistがある。影響は未確定。
次の比較では一時アプリ内の本体だけを通常releaseからコピーし、SHA-256が
`a6f93370bef1a00063a8d1cfe85998ebd49c286fa6b67fbe4f839db514b8c0ee`と一致することを確認した。
通常release自体は変更していない。

## 実機での再試験 3

一時アプリ内の本体を通常releaseと完全に同じファイルにした試行でも、
ユーザーから読み込みと操作の成功報告を得た。診断コードは本体に含まれない。
ResourcesとFrameworksの参照先は通常releaseと同一。ログにSignal 11はなかった。
これだけではアプリ形式による改善と断定できないため、次は通常配置場所の本体を
同じデータ・Mod・入力モードで起動し、同じ診断用ワールドで比較する。
生ログ：`.local/startup-investigation-20260921/physical-startup-3-production-bundle.log`。

## 実機での再試験 4 と現在の結論

通常releaseの本体を、その通常配置場所から起動した。データ・Mod・fullモードは同じ。
診断用アプリ形式も、診断コードも、登録を遅らせるゲートも使っていない。
ユーザーから同じ診断用ワールドで問題なかったとの報告を得た。
ログにゲームパッド接続があり、Signal 11はなかった。
生ログ：`.local/startup-investigation-20260921/physical-startup-4-production-layout.log`。

通常ランチャーの選択中プロファイルは`Joy-Con-Gamepad`。
本体のrelease、データ保存先、Minecraftバージョン、2つのMod参照先は試験と一致した。
ランチャーUIの「遊ぶ」ボタン自体を押す比較は、この試行には含めない。

実機4試行はいずれも成功したが、条件が異なるので同一条件の4連続成功とは扱わない。
通常配置でも成功したため、Info.plist欠落をクラッシュ原因とする根拠は得られなかった。
登録遅延・ポインタ補正・再ビルドを修正として導入する根拠も得られていない。
現在の通常版で、起動時からJoy-Conを有効にして使えることは確認できた。
以前の断続的クラッシュの原因と、長期の安定性は引き続き未確定である。

今回の実機比較では製品コード・通常release・通常プロファイルを変更していない。
再現していない同じ条件の試験を無制限に追加せず、現行構成を維持する。
再発時は通常releaseの`runtime.log`と`runtime.previous.log`が次回起動で入れ替わる前に
保存し、選択したワールド、接続の時点、起動方法、成功時との差を確認する。
