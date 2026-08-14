# Local Prompt Studio

[English](README.md) · [Skill 格式](docs/SKILL_FORMAT.md) · [安全模型](docs/SECURITY_MODEL.md)

Local Prompt Studio 是一个隐私优先、模型无关的提示词 Skill 运行器。Skill 负责描述某个
模型或工作流需要怎样写提示词；Studio 负责本地接口调用、图片引用、推理与正文分流、同一
回复续写、确定性校验和本地历史。

它不捆绑模型权重、厂商提示词文档或云端推理服务。

## 为什么用 Skill

图像、视频、音频和语言模型的语法与限制并不相同，一段写死的系统提示词很难长期维护。
本项目把模型知识放进可查看、可替换的 Skill：

```text
用户想法 + 可选参考图
        ↓
SKILL.md + references + 可选 contract.json
        ↓
兼容 OpenAI 接口的本地服务
        ↓
流式结果 → 规则校验 → 私有本地历史
```

用户可以安装自己信任的 Skill、手写 Skill，或让 Codex 根据用户有权使用的模型文档创建
Skill。Studio 只读取允许的文本作为上下文，绝不执行 Skill 中的脚本。

仓库同时提供 [`codex-skills/create-prompt-skill`](codex-skills/create-prompt-skill/SKILL.md)
作者 Skill。把该文件夹安装到 Codex 的 Skills 目录后，可用 `$create-prompt-skill` 并提供目标
模型版本、有权使用的来源文档、示例请求和预期输出结构。Codex 负责生成可审查的包，Local
Prompt Studio 再独立检查其结构。

## 主要功能

- 支持 Skill 文件夹、单个 `SKILL.md` 或 ZIP 包；ZIP 不会被解压。
- 调用模型前先检查将要载入的文件和输出契约。
- 对接 LM Studio 等兼容 OpenAI 接口的本地服务，支持文字和参考图。
- 服务端支持时，将 reasoning 与最终正文分别显示。
- 第一次 token 预算被推理耗尽时，在同一 assistant turn 内继续生成。
- 校验必需段落、段落顺序、最小长度和图片引用编号。
- 原子写入私有历史，只保存图片文件名，不复制原图。
- 提供零运行时第三方依赖的 CLI 和 Tkinter 图形界面。

## 快速开始

需要 Python 3.11 或更高版本：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\local-prompt-studio.exe --skill examples\storyboard-skill --inspect-skill
.\launch_gui.cmd
```

在本地启动兼容 OpenAI 的服务后，可以运行：

```powershell
.\.venv\Scripts\local-prompt-studio.exe `
  --skill examples\storyboard-skill `
  --idea-file examples\idea.txt `
  --base-url http://127.0.0.1:1234/v1 `
  --model 你的本地模型名
```

最小 Skill 只需要一个 `SKILL.md`。可增加 `references/`、`skill.json` 和
`contract.json`。完整规范见 [Skill 格式说明](docs/SKILL_FORMAT.md)。

## 隐私与安全

默认地址仅为本机回环地址 `127.0.0.1`。除非用户主动改成远程服务，本项目不会上传内容。
Skill 会影响模型输出，应先用检查功能确认内容。加载器只接收有大小上限的 UTF-8 文本，
不运行代码。详见 [安全模型](docs/SECURITY_MODEL.md) 与 [安全政策](SECURITY.md)。

## 开源状态

项目目前处于 alpha 阶段。欢迎提交不同本地服务的兼容性报告，以及拥有清晰授权、独立编写
的模型 Skill。贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)，路线图见
[ROADMAP.md](ROADMAP.md)。项目原创代码与文档采用 [MIT License](LICENSE)；用户提供的
Skill 和模型服务仍受各自条款约束。
