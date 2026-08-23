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
| **`fxdub-receipt`** | 納品セット、48kHzマスター、EBU R128ラウドネス、ダイアログとBGMの音量差（ダッキング）の深さ、再多重化されたMP4ファイルには**両方の**トラックが含まれ、フレームは変更されず、**字幕に表示される人物数とキャスト人数が一致する** | 無音の吹き替え、途中で終わる吹き替え、ダイアログがBGMに埋もれている、目標を外したミックス、**字幕担当者が存在しない人物を映像に登場させている** |
| **`fxdub-dialogue`** | すべてのスクリプト化されたセリフが存在し、順番通りであること、架空のセリフがないこと、キャラクター間のセリフの重複がないこと、途中でセリフが途切れないこと、各キャラクターに1つの声があること、クリップに適合していること | モデルがセリフを創作すること、レンダリング間でキャラクターの声が変わること、次のキュー（合図）を消費するポーズがあること、2人のキャラクターが1つの声に統合されること |

**チェックで失敗した場合、それはツールのバグではなく、発見された問題です。** それを報告してください。合格となるように閾値を調整しないでください。すべてのチェックは、参照している標準または測定された欠陥を示しますので、証拠に基づいて議論することができます。

## シーンのスクリプトが契約書です

演出は、エージェントの頭の中ではなく、スクリプトに存在します。

```json
{
  "clip_duration_s": 10.062,
  "cast": {
    "VOICE": { "description": "off-frame, deep and gritty", "on_frame": false },
    "MAC":   { "description": "on-frame, gritty, weary", "on_frame": true,
               "face": { "frame": 60, "x": 348, "y": 122 } }
  },
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

`on_frame`は、視覚情報がないパッケージでも字幕の欠陥を検出できるようにするものです。 `--scene`を`fxdub-receipt`に渡し、字幕が*主張する*人数と、契約で表示される人数を比較します。納品された映像では、そのチェックに失敗します。字幕担当者は、「**向かい合って立つ二人の男性**」という字幕を、一人しか映っていないシーンに表示しており、この字幕が音声プロンプトとして使用されます。

`--only-speaker MAC`は契約を1つのキャラクターに絞り込みます。これが、**キャラクターごとのトラック**のチェック方法です。それは、そのキャラクターのセリフと、他の誰かが話している場合は*無音*を含んでいるはずです。シーン全体に対してトラックをチェックすると、上記のバグが正確に見えなくなります。

## トランスクリプトを取得する

`fxdub-dialogue`は、単語レベルでダイアライズされたトランスクリプト（`{text, start, end, speaker_id}` per word. Any diarizing ASR will do. `fxdub.vo_graphs.transcribe()`）を読み込み、それを使用してComfyUIグラフを作成します。

```python
from fxdub import vo_graphs

graph = vo_graphs.transcribe("<storage-key>.flac", "run/words")
# -> API-format dict, ready for your own submit path. Nothing is sent from here.
```

## グラフビルダー

`fxdub.vo_graphs`は、VOステージのグラフも作成します。具体的には、音声デザイン、同じエンジンを使用したオーディオ参照、クローンを作成して発声させる、つなぎ合わせる、タイムラインに配置する、ミックスを行うといった処理と、映像ステージでは、フレームを抽出する、リップシンクを行う、多重化するという処理を行います。これらはすべて、代替手段であるAPI JSONをチャットウィンドウに手動で入力する方法を使用すると、セッションとともにグラフが消えてしまい、すでに支払った欠陥が再び発生してしまうためです。

すべてのビルダーは、リポジトリのトラップ検出器によってLintチェックされます。そのため、実際の失敗につながる形状を誤って作成することはできません。その仕組みの2つの例：

- ElevenLabsのクローンノードの自動拡張入力は、実行時に`files.audio0`として扱われます。**決して**そのノード自体のスキーマに記載されている`files.item_1`としては扱われません。また、テスト実行では、誤った名前が問題なく受け入れられます。
- ByteDanceの`pitch_rate`はノード全体で有効であるため、単一のノードで異なるピッチで二人のキャラクターに音声を割り当てることはできません。タイムスタンプは絶対的な出力タイムラインを参照するため、修正は各キャラクターに対して一度ずつ行い、重ね合わせる必要があります。
- リップシンクノードの`speaker_selection`はデフォルトで*モデルに決定させる*設定になっています。この設定を変更しないと、ジョブが完了し、正しいフレーム数のMP4ファイルが適切な長さで出力され、すべてのコンテナチェックをパスしますが、実際には別の人物の口が動いていることになります。ビルダーは座標を固定します。検出器は、その座標が固定されていないグラフに対して失敗します。

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
                                   │
                       (optional)  ▼
                    lip-sync ─► sync one named face to that
                                character's own track, then
                                re-mux the full mix back over it
```

> **「再マルチプレックス」** = 再びマルチプレックスすること：完成したサウンドトラックは、ピクセルを変更せずにビデオコンテナに書き戻されます。「リミックス」のタイプミスではありません。ミキシングは1つ前の段階で行われ、これは再生可能な`dubbed.mp4`を提供します。

**メーターからゲインを調整し、記憶している数値を使用しないでください。** 同じセリフでも、エンジンによって8dBの違いがあります。あるTTSを別のものに置き換えると、VOトラックが-18.34 LUFSから-25.03 LUFSに変化しました。以前のレシピで固定されたゲインを再利用すると、他のすべてのチェックは合格したままで、セリフが7dB沈んでしまいます。

## この設計の良い点は何ですか？

- **字幕はタイミングではなく意味を伝えます。** 字幕を利用したパイプラインは、環境音とダイアログの品質を保証するものであり、文章だけでドアの閉まる音を同期させることはできません。インパクトのあるタイミングを実現するには、イベントタイムラインが必要です。
[ナレッジベース](docs/knowledge-base.md#stage-2b--direct-videoaudio-the-sync-first-alternative)には、直接的なビデオ→オーディオモデルがどのようにネイティブにそれを行うか、およびそのライセンスに関する情報が記載されています。
- **シーンの説明はスクリプトではありません。** キャラクターが言う言葉を記述し、パイプラインがそれを適切な音にします。
- **音声のアイデンティティは無料ではありません。** プロンプトで設計された音声は、*シードに関係なく*非決定的なものです。つまり、承認した音声は、同じプロンプトを再実行しても再現できません。一度キャストし、承認されたオーディオを保存しておき、その後はそれを参照またはつなぎ合わせて使用します。異なるエンジンを使用したクローニングでも、アイデンティティは保持されません。これは、リポジトリのトラップ台帳にある最もコストのかかる教訓であり、検証者の`one_voice_per_character`チェックによって、その教訓が確実に守られます。
- **リップシンクは1つの顔を動かすため、1つのキャラクターのトラックが必要です。** 混合音声を入力すると、すべてのセリフ（映像に映っていない人物のものを含む）が口パクで表示され、それでもすべてのオーディオチェックをパスします。なぜなら、オーディオ自体は変更されていないからです。各キャラクターごとにトラックを入力し、無音にすると、正しいパフォーマンスになります。つまり、キャラクターが聞いている状態になります。結果は*シードに関係なく*非決定的なため、承認されたテイクは保存され、再レンダリングされることはありません。このノードはまた、映像のタイミングも調整します。納品物のフレーム数をチェックし、生の出力ではなく、それを基準に判断します。
- **ミックスの数値は、規格とリスニング調査（BS.1770-5、AES TD1008、JAESダッキング研究）に基づいており、感覚的なものではありません。** また、それらは調整可能なノブであり、好みが測定可能に異なるためです。
- **ガバナンスは機能です。** 許可なく、実在する人物の声をクローンしないでください。EUで公開される合成音声には、Article 50に基づく機械可読マーキング義務が課せられます。レシートJSONは、そのプロベナンス（来歴）追跡の一部となるように作成されており、[KBの公開セクション](docs/knowledge-base.md#publishing--governance-read-before-you-ship-a-dubbed-video)には、どこに投稿するかに応じて、どのような情報開示が必要かが記載されています。特定の人物の声パックは絶対に作成しないでください。ロボコールにも使用しないでください。

## ステータス

**v1.1.1 ― パイプラインが完成し、両方の音声トラックは正常に再生され、映像と音が同期している。** 2人の登場人物が登場する夜の街並みのシーンは、コンテナ契約（48kHz、-18.09 LUFS、セリフは背景音に対して+11.17 LU、161フレームすべてが正常に再生され、長さは10.069秒）において**19/19点**を獲得し、コンテンツ契約においては**11/11点**を獲得した。映像と音が同期されたバージョンでは、同じ契約条件（832×480、161フレーム、両方の音声トラック）が適用され、MACのキャラクターはセリフを言うときには口を開き、そうでないときは閉じている。

`--scene`をパスすると、**19/20点**を獲得します。失敗の原因は明確です。納品された映像の字幕には、一人しか映っていないシーンに二人の男性が表示されています。このチェックは今回のリリースで新しく追加されたものであり、以前から存在していた欠陥を検出しました。197件のテストすべてがCIで緑色になりました。完全な履歴は[CHANGELOG](CHANGELOG.md)にあります。

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
