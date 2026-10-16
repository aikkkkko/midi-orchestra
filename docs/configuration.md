# 配置与扩展

[English](en/configuration.md) · **简体中文**

`midi-orchestra init` 生成私有的 `config.local.json`；已有同名文件时保持原样。`configs/` 下是三份通用模板：`local.example.json`（Windows 本机）、`local-macos.example.json`（macOS 本机）和 `ssh-windows.example.json`（通过 SSH 调用 Windows 渲染机）。默认启用 Surge；模板里的路径和预设哈希由安装脚本生成，或由你自己填写。

`--config` 是全局参数，写在子命令之前：

```bash
midi-orchestra --config config.local.json list
midi-orchestra --config config.local.json render surge_pluck --midi examples/midi/surge_pluck.mid --normalize
```

本机的相对路径以配置文件所在目录为基准。SSH 模式下，已启用引擎的路径填写 Windows 渲染机上的绝对路径，配置检查会核对这一点。`python` 和 `executable` 可以只写命令名，工具会在 PATH 中查找，`doctor` 和渲染使用同一规则。每个引擎各自指定 `python`，环境互相独立，MIDI-DDSP 的 TensorFlow 环境也单独存在。

`engines` 记录可执行文件、采样库和插件的位置；`instruments` 记录音色 ID、program、预设位置、SHA-256 和尾音秒数。已经装好引擎的用户可以直接编辑这份配置，跳过自动下载。

新增 Surge 音色：从 Surge XT 1.3.4 的原厂 FXP 预设中提取 chunk，用 `midi_orchestra.presets.convert_fxp` 封装成 VST3 预设，起一个新的音色 ID，并登记输出文件的 SHA-256。渲染一段短 MIDI 试听、记录来源署名后，即可作为已验证音色使用。封装器使用 Surge XT 1.3.4 的插件 class ID；Windows 和 macOS 的原厂文件生成的预设逐字节相同，两个平台通用。

工具通过 `load_vst3_preset` 载入预设，全程无需打开插件界面，在 SSH 会话中同样可用。Windows 上，自动安装使用独立的官方 Python 运行时，避开部分 Conda 环境自带的旧版 MSVC 运行库；如需指定系统 DLL，可在引擎配置中设置 `msvc_runtime`。macOS 上，Surge 使用安装脚本创建的虚拟环境 `.runtime/surge/env`，FluidSynth 也可以共用这个环境。

Surge 原厂 MKS-70 Warm Pad 文件的内部历史名称是 Buggy Brass，音色以文件路径和 SHA-256 为准。带随机调制的预设每次渲染会有细微差别。
