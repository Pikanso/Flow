# Flow：本地英文视频学习工具

Flow 是 Windows 英文视频逐句练习工具：导入本地视频，离线识别英文并分句，按句重播、慢速播放和循环练习。

**[下载 Windows 版](https://github.com/Pikanso/Flow/releases/latest)** · [源码](https://github.com/Pikanso/Flow)

在 Release 下载 `Flow-v1.0.0-windows-x64.zip`，解压后双击 `Flow.exe`。发布包包含英文识别模型、使用说明和第三方许可文件；不包含个人视频、预览素材或日志。

## Windows 桌面版

双击 `dist\Flow\Flow.exe` 即可打开独立软件窗口，无需安装 Python，也不会打开浏览器。英文识别模型已内置，自动分句可离线使用。单文件版首次打开需要解压内置组件到临时目录，因此启动会稍慢；无需解压或手动安装。

新版采用黑色播放器界面、红色进度条与句子高亮。播放器随窗口大小扩展，保持视频原比例；当前句的识别或导入字幕独立显示在重播按钮上方，长句自动换行。视频下方仅保留“上一句 / 重播 / 下一句”，点击重播始终从当前句开头重新播放。画面内有独立的播放/暂停与 0.5×～2× 倍速控制，暂停后继续从暂停位置播放。导入视频、导入字幕、字幕生成进度、循环、留白、字幕显示、音量与分句编辑收在视频右上角的齿轮设置中。全屏也保留字幕与逐句操作。空格键也可播放/暂停。

界面已移除顶部宣传和底部提示。软件图标为黑底红色小写 `e`，源文件为 `app-icon.svg`；`make_icon.py` 生成包含多种尺寸的 Windows 图标。

打开齿轮面板（首次可点击画面中央“导入视频 / 生成字幕”）→ 导入本地视频 → 生成英文字幕 / 分句 → 查看进度 → 完成后点击“完成，开始学习”，关闭面板并逐句练习。处理准备阶段显示等待状态，识别时按已处理视频时长显示百分比，完成后显示 100%；这不是剩余耗时的预测。已有字幕可直接导入。导出字幕时使用 Windows 保存对话框。退出前请导出修改过的字幕，软件不自动保存练习进度。

运行环境：Windows 10 / 11，64 位，Microsoft Edge WebView2 Runtime（当前电脑已有）。桌面窗口关闭时，该窗口的本地服务会一同停止；运行日志存放在 `%LOCALAPPDATA%\Gengju\desktop.log`。

重新构建桌面版：安装 `desktop-requirements.txt` 的依赖，然后运行 `.venv\Scripts\python.exe build_desktop.py`。打包脚本使用已下载的英文模型。

从源码构建（Windows PowerShell，推荐 Python 3.13 64 位）：

```powershell
git clone https://github.com/Pikanso/Flow.git
cd Flow
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r desktop-requirements.txt
.venv\Scripts\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-base.en', revision='3d3d5dee26484f91867d81cb899cfcf72b96be6c', cache_dir='.models', allow_patterns=['model.bin','config.json','tokenizer.json','vocabulary.txt'])"
.venv\Scripts\python.exe build_desktop.py
```

构建时安装依赖、下载模型需要联网；已发布的 exe 内置模型，日常播放和识别在本机完成。程序使用仅绑定 `127.0.0.1` 的本地服务。

验证源码：

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
node tests/test_subtitles.cjs
```

可通过 `Flow.exe --self-test <报告绝对路径>` 运行桌面集成检查，它会使用内置测试视频、打开测试窗口、写入 JSON 报告并退出。Node.js 仅用于 JavaScript 测试，不是桌面软件的运行依赖。

依赖说明及许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。当前 exe 未进行数字签名。

## 原网页版本

双击 `启动工具.cmd`，然后打开 http://127.0.0.1:8765 。启动窗口需要保持打开，关闭它即停止服务。首次启动安装 Python 依赖；自动识别首次使用下载 `base.en` 模型，之后可以离线使用。

1. 导入已保存在本机的视频。推荐 MP4 / H.264；具体播放格式取决于浏览器。
2. 有字幕：导入匹配的 SRT / VTT。每个字幕块对应一个播放片段，可手动拆分或合并。
3. 无字幕：在齿轮面板点击“生成英文字幕 / 分句”。使用本机 CPU 识别，耗时取决于视频长度和电脑性能。视频临时保存于系统临时目录，任务完成或失败后删除；不会上传到云端。首次模型下载需要联网。
4. 点击句子列表，播放器定位到句首。设置语速、循环和跟读留白，逐句练习。
5. 自动断句依据标点、停顿和长度，不能保证每句都准确。在“调整当前句 / 手动分句”中修改文字、取起点/终点，或拆分/合并句子。
6. 导出字幕保存你的修改；下次重新导入视频和字幕。刷新页面不会保留未导出的修改。

目录中的 `sample.mp4` 与 `sample.srt` 是合成语音示例，可以先导入体验。自动识别、MP4 导入、句尾停止、留白循环及手动拆分/合并已经通过本机测试。

该工具按时间戳播放原视频，不生成独立的切片视频文件。浏览器定位和停止存在少量时间误差。自动识别为英文模型，中文部分的字幕可能不准确。本工具不负责从 B 站下载视频，也不提取画面中烧录的字幕。

## 手动运行

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe server.py
```

服务只监听 `127.0.0.1:8765`；一次处理一个识别任务。使用 Python 3.10 或更高版本。
