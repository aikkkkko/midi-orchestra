# 通过 SSH 调用 Windows 渲染机

[English](en/ssh.md) · **简体中文**

在 Windows 渲染机上安装引擎，在控制电脑（Windows、macOS 或 Linux）上安装本工具。SSH/SCP、Windows OpenSSH 服务、密钥认证和主机指纹验证都使用你自己的系统配置。

1. 复制 `configs/ssh-windows.example.json` 为 `config.local.json`。
2. 把模板别名 `render-host` 换成你已经配置好的 SSH 别名。密码和密钥留在 SSH 自己的配置里，JSON 中只写别名。
3. 把 `work_root` 和 `runner` 设为你选定的 Windows 绝对路径，目录名使用无空格的写法；引擎、插件和预设路径可以包含空格。
4. 填写引擎的 Python、插件和预设路径，以及安装后得到的 `preset_sha256`，替换模板中的占位值 `generated-by-setup`。已启用引擎的路径填写渲染机上的绝对路径；`python`、`executable` 也可以只写命令名（如 `fluidsynth`），`doctor` 会在渲染机的 PATH 中查找。
5. 同步 worker，然后检查并渲染：

```bash
midi-orchestra sync
midi-orchestra doctor
midi-orchestra render surge_pad --midi examples/midi/surge_pad.mid --normalize
```

`sync` 只复制 worker 脚本，引擎、模型和私有配置都保持原位。每次渲染有独立的任务目录，原始输入和准备后的 MIDI 分开保存。SSH 使用 BatchMode 和 StrictHostKeyChecking，只连接指纹已经确认过的主机。

建议给渲染任务准备一个专用目录。远端任务和本地 outputs 里可能包含实际部署路径或输入素材，请保存在私有环境中；发布工具只打包白名单里的文件。

Mac 用户可以同时保留两份配置：一份在本机渲染 Surge 和钢琴，另一份通过 SSH 调用 Windows GPU 机器渲染 MIDI-DDSP 乐器，用 `--config` 切换。
