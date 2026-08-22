<p align="center">
  <a href="README.md">English</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="docs/assets/logo.png" alt="fx-dub" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/fx-dub/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/fx-dub/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/fx-dub/"><img src="https://img.shields.io/pypi/v/fx-dub.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/fx-dub/"><img src="https://img.shields.io/pypi/pyversions/fx-dub.svg" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT"></a>
  <a href="https://mcp-tool-shop-org.github.io/fx-dub/"><img src="https://img.shields.io/badge/landing-page-blue.svg" alt="Landing page"></a>
</p>

**生成されたダビングを、誰かが聞く前に検証します。**

テキスト読み上げモデルは、正確に適切な長さで48kHzステレオを出力し、教科書通りの-18 LUFSでした。しかし、実際にはあなたが書いたことのないセリフを、あなたのキャラクターの声ではない声で話し、途中に2秒の無音部分がありました。

これらの問題は、サンプリングレートと長さからはわかりません。fx-dubは、2つの結果を提供します。1つはコンテナ用、もう1つは**実際に発せられた内容**用です。どちらかが失敗すると、ゼロ以外の値を返して終了します。

```bash
pip install fx-dub
```

```console
$ fxdub-dialogue docs/scenes/night-street.json words.json --only-speaker VOICE
9/10 checks pass
| PASS | line_present:0:VOICE    | Hey, how's it going?
| FAIL | no_invented_speech      | 4 unscripted word(s): not bad can't complain
| PASS | no_overlap              | clean
| PASS | no_internal_straggle    | clean
| PASS | one_voice_per_character | clean
```

この失敗は現実です。`audio reference`モードのモデルは、参照クリップの*セリフ*を再現しただけであり、音色だけではありませんでした。そのため、あるキャラクターのセリフを担当するはずのトラックが、別のキャラクターのセリフを静かに再演しました。実際のテイクの下にミックスすると、まるで2人の男性が互いに話しかけ合っているように聞こえました。サンプリングレート：完璧。長さ：完璧。

## 2つの結果

| | チェック項目 | 検出される問題点 |
|---|---|---|
| **`fxdub-receipt`** | 配信セット、48kHzマスター、EBU R128ラウドネス、セリフとBGMの音量調整（ダッキング）の深さ、再マルチプレックスされたMP4には**両方の**トラックが含まれ、フレームは変更なし | 無音のダビング、途中で切れたダビング、セリフがBGMに埋もれている、ターゲットを外したミックス |
| **`fxdub-dialogue`** | すべてのスクリプト化されたセリフが存在し、順番通りであること、架空のセリフがないこと、キャラクター間のセリフの重複がないこと、途中でセリフが途切れないこと、各キャラクターに1つの声があること、クリップに適合していること | モデルがセリフを創作すること、レンダリング間でキャラクターの声が変わること、次のキュー（合図）を消費するポーズがあること、2人のキャラクターが1つの声に統合されること |

**チェックで失敗した場合、それはツールのバグではなく、発見された問題です。** それを報告してください。合格となるように閾値を調整しないでください。すべてのチェックは、参照している標準または測定された欠陥を示しますので、証拠に基づいて議論することができます。

## シーンのスクリプトが契約書です

演出は、エージェントの頭の中ではなく、スクリプトに存在します。

```json
{
  "clip_duration_s": 10.062,
  "lines": [
    { "speaker": "VOICE", "text": "Hey, how's it going?" },
    { "speaker": "MAC",   "text": "Not bad. Can't complain.",
      "max_gap_s": 0.15,
      "direction": "There's no pause in between. A gap here runs into VOICE's next cue." },
    { "speaker": "VOICE", "text": "Good to hear, good to hear." }
  ]
}
```

`max_gap_s`におけるこの行があるため、検証ツールはグローバルな閾値では見過ごされるテイクを拒否します。その横にある注釈が、数値が0.15である理由です（他の数値ではない理由）。

`--only-speaker MAC`は契約を1つのキャラクターに絞り込みます。これが、**キャラクターごとのトラック**のチェック方法です。それは、そのキャラクターのセリフと、他の誰かが話している場合は*無音*を含んでいるはずです。シーン全体に対してトラックをチェックすると、上記のバグが正確に見えなくなります。

## トランスクリプトを取得する

`fxdub-dialogue`は、単語レベルでダイアライズされたトランスクリプト（`{text, start, end, speaker_id}` per word. Any diarizing ASR will do. `fxdub.vo_graphs.transcribe()`）を読み込み、それを使用してComfyUIグラフを作成します。

```python
from fxdub import vo_graphs

graph = vo_graphs.transcribe("<storage-key>.flac", "run/words")
# -> API-format dict, ready for your own submit path. Nothing is sent from here.
```

## グラフビルダー

`fxdub.vo_graphs`はまた、VOステージのグラフも作成します：音声デザイン、同じエンジンを使用したオーディオ参照、クローンと発声、スプライス、タイムラインへの配置、ミックス。これらは存在するのは、代替手段（API JSONをチャットウィンドウに手動で入力する）を使用すると、セッションとともに消えてしまい、すでに一度支払った欠陥が静かに再導入されてしまうためです。

すべてのビルダーは、リポジトリのトラップ検出器によってLintチェックされます。そのため、実際の失敗につながる形状を誤って作成することはできません。その仕組みの2つの例：

- ElevenLabsクローンノードの自動拡張入力は、実行時に`files.audio0`としてアドレス指定されます（自身のスキーマで宣伝されている`files.item_1`ではありません）。また、ドライランでは、間違った名前が苦情なしに受け入れられます。
- ByteDanceの`pitch_rate`はノード全体で使用されるため、1つのノードで異なるピッチで2人のキャラクターに声を当てることができません。そのタイムスタンプは絶対的な出力タイムラインを参照するため、修正は各キャラクターに対して1回実行し、レイヤー化する必要があります。

グラフの作成は、引数から`dict`への純粋な関数です。**このパッケージ内のものは何も送信、アップロード、または消費しません。**

## 脅威モデル

fx-dubはローカルで実行され、いかなる種類のネットワーク呼び出しも行いません。

- **Data touched:** only the files you name on the command line — FLAC/MP4 masters,
  LUFS manifests, caption text, transcript JSON. It writes one receipt, at the
  `--json` path you choose.
- **Data NOT touched:** no credentials, no API keys, no environment secrets, no
  files outside the paths you pass.
- **Permissions required:** filesystem read on the inputs; filesystem write only if
  you pass `--json`.
- **Network egress: none.** There is no HTTP client here and the runtime dependency
  list is empty by design — CI fails the build if that ever changes.
- **Telemetry: none.** Nothing is collected, counted, or transmitted.

メディアの解析は標準ライブラリのみを使用します。FLAC `STREAMINFO`とMP4アトムは、外部プログラム（`ffprobe`）を呼び出すのではなく、直接デコードされます。不正な入力の場合、クラッシュするのではなく、チェックが失敗します。完全なポリシーについては、[SECURITY.md](SECURITY.md)を参照してください。

## 終了コード

| コード | 意味 |
|---|---|
| `0` | すべてのチェックに合格しました |
| `1` | オーディオが契約を満たしていません - 結果を参照してください |
| `2` | ツールを実行できませんでした - 誤ったパス、不正なJSON、不明なスピーカー |

`1`と`2`は、意図的に区別されています。CIでは、最初のものは結果を読み取ることを期待し、2番目のものは呼び出しが正しくないことを意味します。エラーは、標準出力に`{code, message, hint}`を出力します。そして、`--debug`は再スローされます。

## これらの結果で検証されるパイプライン

fx-dubは、ComfyUIネイティブのダビングパイプラインとして始まり、現在もそうです。[Comfy Cloud](https://cloud.comfy.org)で実行できます。

```
video ─► describe (Florence-2, pinned, single mid-clip frame)
              │ caption.txt
              ▼
        audio prompt (positive claims only — negation collapses in audio-text models)
              ├──────────► ambience bed (ElevenLabs eleven_sfx_v2, 48 kHz, exact duration)
              │                    │ stem_bed.flac
   your script ──────────► dialogue (per-character passes, layered on an absolute timeline)
                                   │ stem_vo.flac
                                   ▼
                    mix bus (48 kHz · dialogue-anchored · −18 LUFS)
                                   │ mix.flac + LUFS manifests
                                   ▼
                        re-mux ─► dubbed.mp4
```

> **「再マルチプレックス」** = 再びマルチプレックスすること：完成したサウンドトラックは、ピクセルを変更せずにビデオコンテナに書き戻されます。「リミックス」のタイプミスではありません。ミキシングは1つ前の段階で行われ、これは再生可能な`dubbed.mp4`を提供します。

**メーターからゲインを調整し、記憶している数値を使用しないでください。** 同じセリフでも、エンジンによって8dBの違いがあります。あるTTSを別のものに置き換えると、VOトラックが-18.34 LUFSから-25.03 LUFSに変化しました。以前のレシピで固定されたゲインを再利用すると、他のすべてのチェックは合格したままで、セリフが7dB沈んでしまいます。

## この設計の良い点は何ですか？

- **キャプションはタイミングではなく意味を伝える。** キャプションを利用したパイプラインは、環境音や会話に適しており、文章だけでドアの閉まる音と完全に同期させることはできない。効果音として重要なタイミングには、イベントのタイムラインが必要であり、[ナレッジベース](docs/knowledge-base.md#stage-2b--direct-videoaudio-the-sync-first-alternative)では、それをネイティブに実行する直接的なビデオ→オーディオモデルと、それらのライセンスが示されている。
- **シーンの説明はスクリプトではない。** 登場人物が言うセリフを記述し、パイプラインがそれを適切な音にする。
- **声のアイデンティティは無料ではない。** プロンプトで生成された声は、*シードに関係なく*決定論的ではなく、承認した声を同じプロンプトを再実行しても再現することはできない。一度キャストを行い、承認されたオーディオを保存し、その後はそれを参照または編集して永久に使用する。異なるエンジンでのクローニングでも、アイデンティティは保持されない。これはリポジトリのトラップ台帳における最も重要な教訓であり、検証者の`one_voice_per_character`チェックによってその教訓が確実に守られる。
- **音量の数値は、規格とリスニング調査（BS.1770-5、AES TD1008、JAESダッキング研究）に基づいているものであり、単なる好みではない**。また、それらは調整可能なパラメータであり、個人の好みが測定可能に異なるためである。
- **ガバナンスは重要な機能である。** 他の人物の声に無断でクローンを作成してはならない。EUで公開される合成音声には、第50条に基づく機械可読形式のマーキング義務があり、その証拠となるJSONファイルが、そのトレーサビリティの一部として構築されている。また、[KBの公開セクション](docs/knowledge-base.md#publishing--governance-read-before-you-ship-a-dubbed-video)には、投稿する場所に応じてどのような情報開示が必要かが記載されている。特定の人物の声を使用した音声パックは、今後一切作成しない。ロボコールにも使用しない。

## ステータス

**v1.0.0 — パイプラインが提供され、両方の検証結果が良好である。** 2人の登場人物が登場する夜の街並みのシーンは、コンテナ契約（48 kHz、-18.09 LUFS、会話+11.17 LU、ベース音に対して、161フレーム intact、10.069秒）で**19/19点**、コンテンツ契約で**11/11点**を獲得した。167回のテスト、CIは良好。完全な履歴は[CHANGELOG](CHANGELOG.md)に記載されている。

| 要素 | 状態 |
|---|---|
| [ハンドブック](https://mcp-tool-shop-org.github.io/fx-dub/handbook/) — インストール、使用方法、シーンのスクリプト、グラフビルダー、検証 | ✅ |
| [設計理由](docs/design/2026-08-21-fxdub-v1.dispatch.md) — すべてのデフォルト設定の背後にある45件の調査結果 | ✅ 外部で検証された引用 ([記録](docs/design/2026-08-21-fxdub-v1.dispatch.verify.md)、リポジトリ内のEd25519証明書) |
| [ナレッジベース](docs/knowledge-base.md) — すべてのオプション、正直なライセンス、測定されたコスト | ✅ |
| [エージェントのオンボーディング](AGENTS.md) + プロジェクトデータベース ([kb/fxdub.db](kb/README.md)) — ノード、モデル、実行、**65件の測定されたトラップ**、決定 | ✅ ライブ; 各セッションで再構築 |
| 効果音イベントタイムライン · ローカルGPUレーン | ⏳ ロードマップ |

## エージェントとLLM向け

[AGENTS.md](AGENTS.md)から開始 — 永続的な操作マニュアル — 次に、ライブ状態については[HANDOFF.md](HANDOFF.md)、その後はトラップ台帳について`kb/fxdub.db`をクエリする。機械可読形式の概要は、[`/fx-dub/llms.txt`](https://mcp-tool-shop-org.github.io/fx-dub/llms.txt)で公開されている。

## トレーサビリティ

このリポジトリでは、まず証拠を記録する開発手法を採用している。グラフはプラットフォームから取得され、レポートからの信頼ではなく、検証（請求フィード、デコードされた出力ヘッダー）される。設計の引用は、アーキテクチャになる前に、外部の異なる系統の検証者によって検証される。測定された数値には、ジョブのUUIDが記録されている。トラップが見つかった場合、同じコミットで検出器、データベースのシード、およびテストを追加する。

## ライセンス

[MIT](LICENSE) — リポジトリとパッケージ。モデルの重みには独自のライセンスが適用される。 [ナレッジベース](docs/knowledge-base.md)は、正直な情報を提供するものである。© 2026 mcp-tool-shop.

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
