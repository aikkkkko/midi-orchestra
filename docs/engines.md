# 音源与引擎

[English](en/engines.md) · **简体中文**

## Surge XT + DawDreamer

已在 Surge XT 1.3.4 / DawDreamer 0.9.0 上验证：CPU 离线渲染，支持多音和力度，默认 48kHz 双声道。Windows x64 和 macOS 的安装脚本都会生成四个固定预设。插件和原厂音色在安装时从官方发布页下载，发布包里只有本项目的代码。

## FluidSynth

Windows 从 [FluidSynth 发布页](https://github.com/FluidSynth/fluidsynth/releases) 下载；macOS 用 Homebrew 安装：`brew install fluid-synth`。再选一个你有权使用的 SF2 音源。FluidSynth 引擎所用的 Python 环境需要 numpy、pretty_midi 和 soundfile：可以安装本项目的 `render` extra；在 macOS 上也可以直接使用安装脚本创建的 `.runtime/surge/env/bin/python`。然后在配置中填写 `executable`、`soundfont_path` 以及准确的来源、作者和许可，并启用 `fluidsynth_sf2`。

适配器使用默认 bank，program 从 0 计数。钢琴专用音源只包含钢琴音色；需要非零 bank、鼓或特殊通道时，可以扩展适配器。推荐的钢琴音源是 [FreePats](https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html)，试听里的钢琴就来自这里。

## MIDI-DDSP

[MIDI-DDSP](https://github.com/magenta/midi-ddsp) 运行在独立的环境中，按需安装：按官方说明安装代码、TensorFlow/DDSP 和预训练权重，在配置中设置它的 `python`，必要时设置 `environment_root`，并启用 `midi_ddsp`。

验证过的组合是 Python 3.8.20、TensorFlow 2.7.0、DDSP 3.2.0、MIDI-DDSP 0.2.6，与 Surge 的 Python 环境相互隔离。这套依赖年代较早，最适合安装在一台带 NVIDIA GPU 的 Windows 机器上，Mac 和其他电脑通过 [SSH](ssh.md) 调用它。权重和 CUDA 运行库从官方渠道获取。

模型提供 13 种乐器，每轨演奏单声部，默认输出 16kHz。小提琴和大提琴已经实际试听过，其他乐器首次使用时建议先试听一小段。默认使用 GPU，GPU 未就绪时任务会提示检查环境；需要用 CPU 渲染时加 `--cpu`。

模型会采样演奏表情，同一 MIDI 每次渲染都略有不同，重要段落可以多渲染几遍再挑选。长休止期间模型会输出低电平噪声（比演奏段低约 10–20dB）：声部较晚进入时，混音时从进入点开始打开该声部，或只渲染有音符的片段再对齐。渲染时间与总时长成正比，休止也计算在内。
