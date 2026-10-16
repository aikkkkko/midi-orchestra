# MIDI Orchestra

[English](README.md) · **简体中文**

MIDI Orchestra 给 AI agent 配了一支乐团，用来做短片的背景音乐、情绪铺底和转场配乐，音色包括钢琴、弦乐、木管、铜管和合成器。告诉 agent 想要的曲风，它会写好 MIDI 并渲染成音频；已有 MIDI 也可以直接交给它。项目附带供 agent 使用的 `render-midi` 技能，也可以在命令行里直接使用。

## 听听效果

[▶ 25 秒组合试听](examples/audio/ensemble.wav)：钢琴先奏出主题，随后小提琴接过旋律，大提琴对位，下面是合成器铺底、低音、拨奏和纹理。曲子由脚本写成 MIDI，每个声部都由本工具渲染。

单独试听：[钢琴](examples/audio/piano.wav) · [小提琴](examples/audio/violin.wav) · [柔和铺底](examples/audio/surge_pad.wav) · [合成低音](examples/audio/surge_bass.wav) · [拨奏](examples/audio/surge_pluck.wav) · [转场纹理](examples/audio/surge_texture.wav)

## 音色

| ID | 音色 | 引擎 | Windows x64 | macOS |
|---|---|---|---|---|
| `surge_pad`、`surge_bass`、`surge_pluck`、`surge_texture` | 柔和铺底、合成低音、拨奏、转场纹理 | Surge XT 1.3.4 原厂预设 | 安装脚本 | 安装脚本 |
| `piano` | 采样钢琴 | FluidSynth + 自选 SF2 音源 | FluidSynth 官方包 + SF2 | Homebrew `fluid-synth` + SF2 |
| `violin`、`viola`、`cello`、`double_bass`、`flute`、`oboe`、`clarinet`、`saxophone`、`bassoon`、`trumpet`、`horn`、`trombone`、`tuba` | 原声乐器 | MIDI-DDSP 神经模型 | 本机运行，建议使用 GPU | 通过 SSH 调用 Windows GPU 渲染机 |

`midi-orchestra list` 会列出全部音色，以及哪些引擎已经启用。

## 让 agent 来用

技能在 [.agents/skills/render-midi/](.agents/skills/render-midi/SKILL.md)。在能发现 `.agents/skills` 的 agent 工作区中打开本项目，或按所用 agent 的方式安装整个技能目录。装好工具（见下文）后，可以直接按曲风提需求：

> 用 render-midi 给我的产品短片写一段 30 秒、温暖有希望感的背景音乐：钢琴主旋律，柔和铺底，轻快的拨奏节奏，大约 90 BPM。每个声部单独输出 WAV 方便混音，并附上音源署名。

agent 会定好调性、速度和段落，写出多轨 MIDI，逐个声部渲染，交回音频和渲染记录。已有 MIDI 也一样，比如“把这个文件的第 1 轨用小提琴渲染出来”。

## 安装

### Windows x64

需要 Python 3.11 x64 和 Microsoft C++ 运行库。在项目目录运行：

```powershell
py -3.11 -m pip install .
py -3.11 scripts/setup_surge.py
midi-orchestra doctor
```

### macOS（Apple 芯片或 Intel）

需要 Python 3.11–3.14，例如 Homebrew 安装的版本。在项目目录运行：

```bash
python3 -m pip install .
python3 scripts/setup_surge.py
midi-orchestra doctor
```

安装脚本从官方发布页下载 Surge XT 1.3.4 并校验 SHA-256（Windows 约 313 MB，含一个独立的 Python 3.11.9 运行环境；macOS 约 400 MB）。macOS 上直接从官方安装包里取出 VST3 插件和原厂音色，放进项目的 `.runtime/` 目录，无需管理员安装。随后脚本生成四种合成器音色，写入你自己的 `config.local.json`，原有配置会先备份。

钢琴需要再装 FluidSynth（macOS 上用 `brew install fluid-synth`）和一个 SoundFont；MIDI-DDSP 乐器运行在独立的 GPU 环境中，见[音源与引擎](docs/engines.md)。命令行工具本身只用 Python 标准库，任何电脑都可以通过 SSH 调用 Windows 渲染机，见 [SSH 渲染](docs/ssh.md)。真实连接信息只保存在你的私有配置里。

## 命令行渲染

```bash
midi-orchestra list
midi-orchestra render surge_pad --midi examples/midi/surge_pad.mid --normalize
midi-orchestra render violin --midi song.mid --track 1 --normalize
```

每次渲染输出到 `outputs/<job>/`：

- `mix.wav`：24bit PCM 音频
- `prepared.mid`：实际演奏的 MIDI
- `render.json`：音频规格、耗时、峰值和预设校验值
- `CREDITS.txt`：引擎、音色和来源署名

原始 MIDI 保持原样，每次渲染写入新的或空的目录。多种乐器用 `--track` 逐轨渲染，再把 WAV 混音。[examples/CREDITS.md](examples/CREDITS.md) 记录了上面试听素材的完整制作流程。

## 使用小贴士

- MIDI-DDSP 乐器每轨演奏单声部，输出 16kHz。每次渲染的演奏表情都略有不同，重要段落可以多渲染几遍，挑最好的一遍。
- 钢琴和合成器可以弹和弦。鼓轨（MIDI 第 10 通道）交给常用的鼓工具处理。
- 每个 Surge 音色 ID 固定使用一个预设，CC 和弯音交给合成器处理。
- 引擎、采样库和模型来自各自的项目，适用各自的许可。发布音频时请一并保留它们的署名。

## 文档

[配置](docs/configuration.md) · [音源与引擎](docs/engines.md) · [SSH 渲染](docs/ssh.md) · [agent 技能](docs/agent-skill.md) · [验证记录](docs/validation.md) · [发布与隐私](docs/releasing.md)

## 开发

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/audit_release.py .
```

试听素材可以完整复现：[scripts/generate_examples.py](scripts/generate_examples.py) 生成 MIDI，[scripts/mix_examples.py](scripts/mix_examples.py) 把渲染好的声部混音。

## 许可

项目原创代码采用 MIT 许可。第三方引擎、预设、采样和模型适用各自的许可，见 [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md)。
