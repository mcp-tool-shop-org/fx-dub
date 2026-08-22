<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.md">English</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

**在任何人听到之前，先验证生成的配音。**

您的文本转语音模型以 48 kHz 立体声输出，并且持续时间完全正确，LUFS 值也达到了标准的 -18 LUFS。但它还说了一句您从未写过的台词，而且声音也不是您角色的声音，中间还出现了两秒的空白。

这些问题无法通过采样率和时长来检测。fx-dub 会为您提供两个验证结果——一个用于容器，另一个用于**实际说的内容**——并且当任何一项不合格时，程序会返回非零值并退出。

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

这种失败是真实存在的。在 `audio reference` 模式下，某个模型重现了其参考片段的*对话内容*，而不仅仅是音色——因此，原本应该只包含一个角色台词的音频轨道，却意外地重新说出了另一个角色的台词。当将其与实际录制的版本混合在一起时，听起来就像两个人同时说话。采样率：完美。时长：完美。

## 这两个验证结果

| | 检查项目 | 检测到的问题 |
|---|---|---|
| **`fxdub-receipt`** | 交付成果集、48 kHz 母带文件、EBU R128 音量标准、对话对背景音乐的动态范围调整深度，重新混合后的 MP4 文件包含**两个**音轨，帧数据完整。 | 静默配音、截断的配音、对话被淹没在背景音乐中、未能达到目标值的混音效果。 |
| **`fxdub-dialogue`** | 所有剧本中的台词都存在且顺序正确，没有自行添加的台词，没有角色之间的重叠，没有中间出现停顿，每个角色的声音都是唯一的，与片段匹配。 | 模型自行编写台词、角色在不同渲染之间发生变化、一个停顿导致下一个提示被忽略、两个角色合并成一个声音。 |

**失败的检查是一个发现，而不是工具中的错误。** 请报告它；切勿调整阈值以使其显示为“通过”。每个检查都会引用其所依据的标准或检测到的缺陷，因此您可以根据证据对其进行讨论。

## 剧本是合同

导演的意图体现在剧本中，而不是在代理人的脑海中：

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

`max_gap_s` 中对该台词的处理方式，就是验证器拒绝某个片段的原因，而如果使用全局阈值，则会忽略这个问题。旁边的注释说明了为什么这个数值是 0.15 而不是其他数值。

`--only-speaker MAC` 将合同缩小到单个角色，这就是您检查**每个角色的音频轨道**的方式：它应该包含该角色的台词以及*静默*，在其他角色说话时保持静默。将一个音频轨道与整个场景进行比较，恰好会隐藏上述问题。

## 获取转录文本

`fxdub-dialogue` 读取逐字记录的对话脚本——`{text, start, end, speaker_id}` per word. Any diarizing ASR will do. `fxdub.vo_graphs.transcribe()`，并构建 ComfyUI 图表：

```python
from fxdub import vo_graphs

graph = vo_graphs.transcribe("<storage-key>.flac", "run/words")
# -> API-format dict, ready for your own submit path. Nothing is sent from here.
```

## 图表生成器

`fxdub.vo_graphs` 还会构建 VO 阶段的图表：语音设计、使用相同引擎的音频参考、克隆和发声、拼接、放置在时间轴上、混合。这些图表的存在是因为，如果采用另一种方法——手动将 API JSON 输入到聊天窗口中——生成的图表会在会话结束后消失，并且可能会悄无声息地重新引入已经解决过的缺陷。

每个生成器都由存储库中的陷阱检测器进行检查，因此那些会导致实际失败的形状不会意外地被重新编写。以下是其中两个示例：

- ElevenLabs 克隆节点的自动扩展输入在运行时被指定为 `files.audio0`——**而不是**其自身架构中声明的 `files.item_1`——并且一次测试会接受错误的名称，而没有任何提示。
- ByteDance 的 `pitch_rate` 是节点全局的，因此一个节点不能以不同的音高来控制两个角色的声音。它的时间戳指向绝对输出时间轴，因此解决方案是为每个角色进行一次处理，然后将它们分层叠加。

构建图表是一个纯函数，其输入是参数，输出是 `dict`。**此包中的任何内容都不会提交、上传或花费。**

## 威胁模型

fx-dub 在本地运行，并且不会进行任何类型的网络调用。

- **涉及的数据：** 仅为命令行中指定的文件——FLAC/MP4 母带文件、LUFS 清单、字幕文本、转录 JSON。它会写入一个验证结果，路径由您选择的 `--json` 指定。
- **不涉及的数据：** 不涉及任何凭据、API 密钥、环境秘密或您传递的路径之外的文件。
- **所需的权限：** 对输入文件进行文件系统读取；如果传递了 `--json`，则可以对文件系统进行写入。
- **网络输出：无。** 此处没有 HTTP 客户端，并且运行时依赖项列表为空，这是出于设计考虑——如果情况发生变化，CI 将导致构建失败。
- **遥测：无。** 不会收集、计数或传输任何数据。

媒体解析仅使用标准库：FLAC `STREAMINFO` 和 MP4 原子直接解码，而不是通过调用 `ffprobe` 来进行处理。格式不正确的输入会导致检查失败，而不是崩溃。完整的策略请参见 [SECURITY.md](SECURITY.md)。

## 退出代码

| 代码 | 含义 |
|---|---|
| `0` | 所有检查都通过 |
| `1` | 音频未能满足其合同要求——请阅读验证结果。 |
| `2` | 该工具无法运行——路径错误、JSON 格式不正确、未知说话者。 |

`1` and `2` stay distinct on purpose: in CI the first wants its receipt read, the
second means the invocation is wrong. Errors print `{code, message, hint}` on
stderr; `--debug` re-raises instead.

## 这些验证结果所验证的流水线

fx-dub 最初是一个 ComfyUI 原生的配音流水线，现在仍然是。它可以在 [Comfy Cloud](https://cloud.comfy.org) 上运行：

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

> **“重新混合”** = 重新多路复用：完成的音轨会写回到视频容器中，像素保持不变。这不是“混音”的笔误——混音发生在之前的阶段；这是为您提供一个可播放的 `dubbed.mp4` 的步骤。

**根据仪表进行增益调整，而不是依赖于记忆中的数值。** 在同一台词上，不同的引擎可能会相差 8 dB：将一个 TTS 替换为另一个会导致 VO 音频轨道的音量从 -18.34 LUFS 变为 -25.03 LUFS。如果重用先前配方中固定的增益值，将会使对话被降低 7 dB，而所有其他检查都显示为“通过”。

## 这种设计的优点是什么

- **字幕承载意义，而非时间信息。** 基于字幕的流水线适用于环境音和对话；它绝不可能仅通过文字来同步门砰的声音。需要影响力的时间点时，则需要一个事件时间轴——[知识库](docs/knowledge-base.md#stage-2b--direct-videoaudio-the-sync-first-alternative) 提供了直接的视频→音频模型，这些模型可以原生地实现这一功能，并列出了它们的许可证。
- **场景描述不是剧本。** 你编写的是你的角色所说的话；流水线的作用是让它们听起来正确。
- **语音身份并非免费提供。** 通过提示设计的语音是非确定性的——*无论种子如何*——你认可的语音都无法通过重新运行相同的提示来恢复。一次性选择，保留已批准的音频，然后永久地引用或拼接它。跨引擎克隆也不能保证语音身份的一致性。这是该仓库中“陷阱记录”中最昂贵的教训，而验证器`one_voice_per_character`检查就是确保人们从中学习的方式。
- **音量数值来自标准和听觉研究**（BS.1770-5、AES TD1008、JAES 降音量研究），而不是主观感觉——而且它们是旋钮，因为偏好在可测量程度上有所不同。
- **治理是一项功能。** 未经同意，请勿克隆真实人物的语音。在欧盟发布的合成语音需要遵守第50条规定的机器可读标记义务；收据 JSON 的构建是为了成为该来源跟踪的一部分，并且[知识库中的发布部分](docs/knowledge-base.md#publishing--governance-read-before-you-ship-a-dubbed-video) 告知你在发布内容时需要披露的内容。绝不允许存在特定人物的语音包，尤其不能用于机器人电话。

## 状态

**v1.0.0 — 流水线已交付，并且两个收据均为“通过”。** 一个包含两个角色的夜间街道场景在容器契约（48 kHz、-18.09 LUFS、对话 +11.17 LU，背景音量，161 帧完整，10.069 秒）中获得了 **19/19** 分，在内容契约中获得了 **11/11** 分。进行了 167 次测试，CI 测试通过。完整的历史记录位于 [CHANGELOG](CHANGELOG.md) 中。

| 部分 | 状态 |
|---|---|
| [手册](https://mcp-tool-shop-org.github.io/fx-dub/handbook/) — 安装、使用方法、场景脚本、图形构建器、验证。 | ✅ |
| [设计原理](docs/design/2026-08-21-fxdub-v1.dispatch.md) — 每个默认设置背后都有 45 个来源信息。 | ✅ 外部验证的引用 ([记录](docs/design/2026-08-21-fxdub-v1.dispatch.verify.md)，Ed25519 收据位于仓库中)。 |
| [知识库](docs/knowledge-base.md) — 所有选项、真实的许可证、可测量的成本。 | ✅ |
| [代理 onboarding](AGENTS.md) + 项目数据库 ([kb/fxdub.db](kb/README.md)) — 节点、模型、运行、**65 个可测量的陷阱**、决策。 | ✅ 正在运行；每个会话都会重新构建。 |
| 音效事件时间轴 · 本地 GPU 通道。 | ⏳ 路线图。 |

## 适用于代理和 LLM

从 [AGENTS.md](AGENTS.md) 开始 — 这是持久的操作手册 — 然后是 [HANDOFF.md](HANDOFF.md)，用于获取实时状态，然后查询 `kb/fxdub.db` 以获取陷阱记录。机器可读的摘要发布在 [`/fx-dub/llms.txt`](https://mcp-tool-shop-org.github.io/fx-dub/llms.txt)。

## 来源

该仓库采用“先收据后开发”的方法：图形是从平台提取并进行验证（账单信息、解码的输出标头），而不是从报告中获取；设计引用在成为架构之前，会通过外部的不同类型的验证器进行验证；可测量的数字携带其作业 UUID。当发现一个陷阱时，相同的提交将添加检测器、数据库种子和测试。

## 许可证

[MIT](LICENSE) — 仓库和软件包。模型权重具有自己的许可证；[知识库](docs/knowledge-base.md) 是真实的地图。© 2026 mcp-tool-shop。

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
