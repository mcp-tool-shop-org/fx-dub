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

**在任何人听到之前，验证生成的配音。**

您的文本转语音模型返回了 48 kHz 立体声，并且持续时间完全正确，LUFS 值也达到了标准的 -18 LUFS。但它还说了一句您从未写过的台词，而且声音也不是您角色的声音，中间还出现了两秒的空白。

这些问题都无法通过采样率和时长来检测。fx-dub 会为您提供两份报告——一份是关于音频文件的，另一份是关于实际说了什么内容的——并且当任何一项检查失败时，程序会以非零状态退出。

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

这种失败是真实存在的。在 `audio reference` 模式下，一个模型重现了其参考片段的*对话内容*，而不仅仅是音色——因此，原本应该只包含一个角色台词的音频轨道，却意外地重新说出了另一个角色的台词。当将其与实际录制的版本混合在一起时，听起来就像两个人同时说话一样。采样率：完美。时长：完美。

## 两份报告

| | 检查项目 | 检测到的问题 |
|---|---|---|
| **`fxdub-receipt`** | 交付内容，48 kHz 母带文件，EBU R128 音量标准，对话对背景音乐的动态范围调整深度，重新混合后的 MP4 文件包含**两个**音轨，帧数完整，**字幕中的人物数量与演员阵容相符** | 静默配音、截断的配音、对话被淹没在背景音乐中、未能达到目标的混音效果，**字幕人员虚构了场景中出现的人物** |
| **`fxdub-dialogue`** | 所有剧本中的台词都已呈现并按顺序播放，没有自行添加的台词，没有角色之间的重叠，没有中间停顿，每个角色都有自己的声音，与片段相符 | 模型自行添加了台词，一个角色的声音在不同的渲染中发生了变化，一段停顿导致下一句台词被省略，两个角色合并成了一个声音 |

**检查失败表示发现了问题，而不是工具中的错误。** 请报告；切勿调整阈值以使其显示为“通过”。每个检查都会引用其所依据的标准或检测到的缺陷，因此您可以根据证据对其进行质疑。

## 场景剧本是合同

导演的意图体现在剧本中，而不是在代理人的脑海中：

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

`max_gap_s` 在该行中的作用是，验证器会拒绝使用全局阈值可以接受的录音。旁边的注释说明了为什么这个数值是 0.15 而不是其他数值。

`on_frame` 使一个不包含视觉信息的软件包能够检测字幕缺陷。将 `--scene` 传递给 `fxdub-receipt`，它会比较字幕*声称*的人物数量与合同中声明的可见人物数量。在交付的版本中，此检查失败：字幕人员在一组只有一个人出现的镜头上写了“两个男人……面对面”，而这段字幕正是用于生成音频提示的。

`--only-speaker MAC` 将合同缩小到单个角色，这就是您如何检查**每个角色的单独音轨**：它应该包含该角色的台词以及*静默*，在其他角色说话时保持静默。将一个音轨与整个场景进行比较，恰好会隐藏上述错误。

## 获取转录文本

`fxdub-dialogue` 读取逐字记录的、带有时间戳的转录文本——`{text, start, end, speaker_id}` per word. Any diarizing ASR will do. `fxdub.vo_graphs.transcribe()`，并构建 ComfyUI 图表：

```python
from fxdub import vo_graphs

graph = vo_graphs.transcribe("<storage-key>.flac", "run/words")
# -> API-format dict, ready for your own submit path. Nothing is sent from here.
```

## 公共 API — `fxdub.verify`

**v1.2.0 版本的新功能。** 这两个控制台脚本用于验证一段*视频配音*。 它们的核心功能——将脚本与实际语音进行匹配——并非特定于视频，而是被导出为一个明确且稳定的接口，以便其他工具可以基于此进行构建，而不是导入可能发生变化的内部组件。

```python
from fxdub import verify

lines = [{"speaker": "narrator", "text": "Chapter two continues the tale."}]
result = verify.align_lines(lines, words)      # words: the transcript above

result.missing            # scripted lines that were never spoken
result.invented_words     # rendered tokens no scripted line claimed

verify.check_all_lines_present(result)   # -> Check(name, ok, detail, traces_to)
verify.check_no_invented_speech(result)
verify.check_one_voice_per_line(result)
```

这三个要素适用于任何将编写好的文本转换为生成语音的流水线：**脚本中要求的台词必须被说出，脚本中没有要求的台词则不能被说出，并且一个角色必须由一个声音来演绎，即他们自己的声音。** 在将其公开之前，这些要素已经通过第二个代码库进行了验证——在 EPUB 到有声读物渲染器中，发现了四种内容缺陷（一个带有旁注的脚注、一个在部分渲染中被删除并报告为成功的章节、三个角色被合并为一个声音、标记被当作散文朗读）。这些缺陷都记录在 [`tests/test_verify.py`](tests/test_verify.py) 中，还有一个干净的对照组，它必须报告没有任何问题。

API 中**不**包含的内容：转录（fx-dub 使用提供的单词时间戳——这就是它没有依赖项的原因）、阈值（所有阈值都与在某种媒介中通过耳朵捕捉到的缺陷相关，因此它们属于拥有策略的调用者），以及特定于媒介的检查——重叠、行尾延迟、片段匹配、音量衰减、字幕与角色语音的同步。如果某个检查在您的媒介中无法有意义地触发，那么它比没有检查更糟糕，因为它会被误认为通过。

`fxdub-dialogue` 本身就是这个 API 的一个消费者——它通过 `verify` 计算其内容验证结果，并且仅添加使收据成为*配音*收据的内容。这通过测试来强制执行，这些测试会破坏 `verify`，并要求 CLI 也随之崩溃，因此公共路径不能悄悄地变成一个没有人使用的路径。

## 图表生成器

`fxdub.vo_graphs` 还会构建 VO 阶段的图表：语音设计、使用相同引擎的音频参考、克隆和发声、拼接、放置在时间轴上、混合——以及画面阶段：帧提取、唇形同步和多路复用。这些图表的存在是因为，如果采用另一种方法——手动将 API JSON 输入到聊天窗口中——生成的图表会在会话结束后消失，并且可能会悄无声息地重新引入已经解决的问题。

每个生成器都由存储库的陷阱检测器进行检查，因此那些会导致实际失败作业的形状不会意外地被重新编写。以下是其中两个示例：

- ElevenLabs 克隆节点的自动扩展输入在运行时被标记为 `files.audio0`——**而不是**其自身架构中声明的 `files.item_1`——并且在进行测试时，它会接受错误的名称而不会发出任何警告。
- ByteDance 的 `pitch_rate` 是节点全局的，因此一个节点不能以不同的音调来控制两个角色的声音。它的时间戳指向绝对输出时间轴，因此解决方案是为每个角色执行一次处理，然后将它们分层叠加。
- 唇形同步节点的 `speaker_selection` 默认设置为*让模型自行决定*。如果将其保持未固定状态，则作业会完成，返回一个正确帧数且时长正确的 MP4 文件，并且通过所有容器检查——但画面中显示的是错误人物的嘴巴在动。生成器会固定坐标；检测器会拒绝不包含这些坐标的图表。

构建图表是一个纯函数，其输入是参数，输出是 `dict`。**此软件包中的任何内容都不会提交、上传或花费任何费用。**

## 威胁模型

fx-dub 在本地运行，并且不会进行任何类型的网络调用。

- **涉及的数据：** 仅为命令行中指定的文件——FLAC/MP4 母带文件、LUFS 清单、字幕文本、转录 JSON。它会写入一份报告，路径由您选择的 `--json` 指定。
- **不涉及的数据：** 不涉及任何凭据、API 密钥、环境秘密或您传递的路径之外的文件。
- **所需的权限：** 对输入文件进行文件系统读取；如果传递了 `--json`，则可以对文件系统进行写入。
- **网络出口：无。** 此处没有 HTTP 客户端，并且运行时依赖项列表为空，这是出于设计考虑——如果情况发生变化，CI 会导致构建失败。
- **遥测数据：无。** 不会收集、计数或传输任何数据。

媒体解析仅使用标准库：FLAC `STREAMINFO` 和 MP4 原子直接解码，而不是通过调用 `ffprobe` 来进行处理。格式错误的输入会导致检查失败，而不是崩溃。完整的策略请参见 [SECURITY.md](SECURITY.md)。

## 退出代码

| 代码 | 含义 |
|---|---|
| `0` | 所有检查均通过 |
| `1` | 音频未能满足合同要求——请阅读报告 |
| `2` | 工具无法运行——路径错误、JSON 格式不正确、未知说话者 |

`1` and `2` stay distinct on purpose: in CI the first wants its receipt read, the
second means the invocation is wrong. Errors print `{code, message, hint}` on
stderr; `--debug` re-raises instead.

## 此流水线验证的收据

fx-dub 最初是一个 ComfyUI 原生的配音流水线，现在仍然是。它运行在：
[Comfy Cloud](https://cloud.comfy.org) 上。

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

> **“重新复用”** = 重新多路复用：完成的音轨会写回视频容器中，像素保持不变。这不是“混音”的笔误——混音发生在之前的阶段；这是生成可播放的 `dubbed.mp4` 的步骤。

**从仪表盘进行增益调整，而不是依赖记忆中的数字。** 在同一设置下，不同引擎的差异高达 8 dB：将一个 TTS 替换为另一个，会将一段人声从 −18.34 LUFS 调整到 −25.03 LUFS。如果重复使用先前配方中固定的增益值，可能会使对话声音降低 7 dB，而所有其他检查都显示为绿色。

## 这个设计的优点是什么？

- **字幕承载意义，而不是时间信息。** 基于字幕的流水线适用于环境音和对话；它绝不会仅通过文字同步一扇门的关门声。需要影响力的时间点时，则需要一个事件时间轴——
[知识库](docs/knowledge-base.md#stage-2b--direct-videoaudio-the-sync-first-alternative) 提供了直接的视频→音频模型，这些模型可以原生地实现同步，并列出了它们的许可证。
- **场景描述不是剧本。** 你编写你的角色所说的话；流水线让它们听起来正确。
- **声音身份不是免费的。** 通过提示设计的语音是非确定性的 *无论种子如何*——你批准的声音不能通过重新运行相同的提示来恢复。一次性选择演员，保留已批准的音频，然后永久引用或拼接它。跨引擎克隆也不能保持声音身份。这是存储库中“陷阱记录”中最昂贵的教训，验证器对 `one_voice_per_character` 的检查就是确保其持续学习的方式。
- **唇形同步驱动一个面部表情，因此需要一个角色的音轨。** 将混合音频输入，它会为每一行对话进行口型匹配——包括那些属于不在画面中的角色的对话——并且仍然通过所有音频检查，因为音频本身没有改变。如果输入每个角色的单独音轨，那么静默将成为正确的表演：角色在倾听。结果是非确定性的 *无论种子如何*，因此会保留已批准的片段，而不会重新渲染。该节点还会重新调整图像的时间；请确认可交付成果中的帧数，而不是其原始输出。
- **混合音量来自标准和听觉研究**（BS.1770-5、AES TD1008、JAES 降噪研究），而不是感觉——而且它们是旋钮，因为偏好在可测量程度上有所不同。
- **治理是一项功能。** 未经同意，请勿克隆真实人物的声音。在欧盟发布的合成语音需要符合第 50 条的机器可读标记要求；收据 JSON 的设计是为了成为该来源跟踪的一部分，并且 [知识库中的发布部分](docs/knowledge-base.md#publishing--governance-read-before-you-ship-a-dubbed-video) 告知你在发布时需要披露的内容。绝不允许存在特定人物的语音包，也不用于机器人电话。

## 状态

**v1.2.0——流水线已交付，两个收据都显示为绿色，画面与口型同步，并且对齐核心现在是一个明确的公共 API。** 在一个包含两个角色的夜间街道场景中，该系统在容器契约（48 kHz，-18.09 LUFS，对话 +11.17 LU，背景音乐，161 帧完整，10.069 秒）和内容契约上都获得了 **19/19** 的分数。在口型同步的变体中，它保持了相同的契约——832 × 480，161 帧，两个音轨——MAC 的嘴在说台词时是张开的，而在画面外角色说话时是闭上的。

一旦您通过 `--scene`，它将获得 **19/20** 的分数，并且失败是真实的：交付的运行中的字幕声称在一个只有一个人的场景中出现了两个人。这个检查捕捉到了一种之前一直显示为通过的缺陷。**277 个测试**，CI 显示为绿色。完整的历史记录在 [CHANGELOG](CHANGELOG.md) 中。

此版本添加了 [`fxdub.verify`](#the-public-api--fxdubverify)——一个明确的、与媒介无关的接口，其他工具可以基于此进行构建——并且修复了两个在测试套件中无法检测到的缺陷：一个已提交的收据携带了写入它的机器的绝对路径，以及一个 CI 触发器，它在每次发布时都会运行完整的矩阵两次。现在，这两个缺陷都有了检测器，并且都通过真实的修复前字节进行了验证。

| 部分 | 状态 |
|---|---|
| [手册](https://mcp-tool-shop-org.github.io/fx-dub/handbook/) — 安装、使用方法、场景脚本、图形构建器、验证。 | ✅ |
| [设计原理](docs/design/2026-08-21-fxdub-v1.dispatch.md) — 每个默认设置背后都有 45 个来源的发现。 | ✅ 外部验证了引用的信息（[记录](docs/design/2026-08-21-fxdub-v1.dispatch.verify.md)，Ed25519 收据在存储库中）。 |
| [知识库](docs/knowledge-base.md) — 每个选项、诚实许可证、测量的成本。 | ✅ |
| [代理入职](AGENTS.md) + 项目数据库（[kb/fxdub.db](kb/README.md））— 节点、模型、运行、**86 个已测量陷阱**、决策。 | ✅ 实时；每次会话都会重新构建。 |
| 音效事件时间轴 · 本地 GPU 通道。 | ⏳ 路线图。 |

## 供代理和 LLM 使用

从 [AGENTS.md](AGENTS.md) 开始——这是持久的操作手册——然后是 [HANDOFF.md](HANDOFF.md），了解实时状态，然后查询 `kb/fxdub.db` 以获取陷阱记录。机器可读的摘要已发布在 [`/fx-dub/llms.txt`](https://mcp-tool-shop-org.github.io/fx-dub/llms.txt) 上。

## 来源

此存储库采用“先收据后开发”的方法：图形是从平台中提取并进行验证（账单信息、解码的输出标头），而不是从报告中获取；设计引用在成为架构之前，会通过外部的不同类型的验证器进行验证；测量的数字带有它们的作业 UUID。当发现陷阱时，相同的提交会添加检测器、数据库种子和测试。

## 许可证

[MIT](LICENSE) — 存储库和软件包。模型权重具有自己的许可证；[知识库](docs/knowledge-base.md) 是诚实的地图。© 2026 mcp-tool-shop。

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
