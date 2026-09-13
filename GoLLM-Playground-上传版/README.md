# GoLLM-Playground

一个**纯 LLM 方案**的围棋 AI 对弈引擎：用大模型 API（智谱 / 千帆）做落子思考，用本地 Python 代码做完整围棋规则校验，对外走标准 **GTP（Go Text Protocol）** 协议，可以和其他自制围棋 AI / 围棋界面互相对弈。

> 棋力：业余 1~3 段水平，不稳定，会出现低级失误。
> 定位：教学、解说、入门陪练、AI 对战实验。不适合中高水平对战机器人。

---

## 一、它能做什么

| 能力 | 说明 |
| --- | --- |
| 人机对弈 | 终端命令行直接下棋（`python main.py`） |
| 对接围棋界面 | 通过 GTP 接入 Sabaki 等 GUI，可视化下棋 |
| AI vs AI | 与任何实现了 GTP 协议的围棋 AI（别人自制的也行）互相对弈 |
| 规则校验 | 提子、禁着点（自杀）、打劫、终局计分全部由本地代码保证，LLM 不负责规则 |

## 二、架构

```
┌─────────────┐   GTP 协议   ┌──────────────────────┐
│  Sabaki GUI │ ◄──────────► │   gtp_server.py      │
│  其他自制AI │              │   GTP 命令解析        │
└─────────────┘              │        │             │
                             │        ▼             │
                             │   llm_go_player.py   │  ← 智谱 / 千帆 API
                             │   (大模型选点思考)    │
                             │        │             │
                             │        ▼             │
                             │   go_board.py        │  ← 规则校验（唯一权威）
                             │   (提子/打劫/禁着点)  │
                             └──────────────────────┘
```

关键设计：**LLM 只负责"想下哪里"，规则全部由本地 `go_board.py` 说了算**。LLM 输出非法落子时，规则模块会拦截并自动转为 pass，保证对局永远合法。

## 三、安装

需要 Python 3.9+。

```bash
pip install -r requirements.txt
```

## 四、配置 API Key

```bash
# 1. 复制示例配置
cp .env.example .env
```

> Windows 下是：`copy .env.example .env`

```bash
# 2. 编辑 .env，填入密钥
ZHIPU_API_KEY=你的智谱key
ZHIPU_MODEL=glm-4-flash
```

- 智谱 Key 申请：https://open.bigmodel.cn/ （免费额度可用 glm-4-flash）
- 想用千帆：填 `QIANFAN_API_KEY`，并在 `.env` 里设置 `LLM_PROVIDER=qianfan`

## 五、使用

### 1. 终端人机对战

```bash
python main.py
```

落子用 GTP 坐标（如 `D4`、`K10`），`pass` 停一手，`quit` 退出。

### 1.5 网页版对局（浏览器下棋，推荐体验）

```bash
pip install -r requirements.txt   # 确保已安装 flask
python web_server.py
```

然后浏览器打开 http://127.0.0.1:5000

- 你执白（AI 执黑先行），**点击棋盘落子**，AI 会自动回应
- 支持 Pass、重新开始，右侧有对局日志与轮次/提子信息
- 连续两次 pass 自动终局并显示简化计分
- LLM 若输出非法落子，规则引擎自动拦截并转 pass（日志中可见）

### 2. 接入 Sabaki 可视化下棋（推荐）

1. 下载安装 [Sabaki](https://sabaki.yichuanshen.de/)（免费）
2. Sabaki → 文件 → 首选项 → 引擎 → 添加引擎
3. 填写：

```
名称：GoLLM
命令：python
参数：gtp_server.py
（参数也可以直接写完整路径，如 C:\...\gtp_server.py）
```

4. 新建对局，黑白任意一方选 GoLLM 引擎，即可下棋

### 3. 和其他自制 AI 对弈（核心目标）

1. 你的 AI（或别人的 AI）只要能通过标准输入输出跑 **GTP 协议**，就能互下
2. 在 Sabaki 里同时添加两个引擎：GoLLM + 对方 AI
3. 新建对局：黑方 = GoLLM，白方 = 对方 AI → 自动对弈

> 不依赖任何特定语言：Python / C / C++ / JS 写的 GTP 引擎都能互通。

### 4. 命令行自测 GTP

```bash
python gtp_server.py
```

输入：

```
boardsize 19
clear_board
genmove B
showboard
quit
```

## 六、项目结构

```
GoLLM-Playground/
├── go_board.py         # 棋盘 + 围棋规则校验（提子/打劫/禁着点/终局计分）
├── llm_go_player.py    # LLM 棋手：智谱/千帆 API 选点
├── gtp_server.py       # GTP 协议服务器（对接 Sabaki / 其他自制 AI）
├── main.py             # 终端人机对战
├── web_server.py       # 网页版后端（Flask，浏览器下棋）
├── webui/
│   └── index.html      # 网页版前端（Canvas 棋盘）
├── test_rules.py       # 规则引擎自测
├── requirements.txt    # 依赖
├── .env.example        # 环境变量模板（复制为 .env 使用）
└── .gitignore
```

## 七、局限与后续方向

**已知局限：**
- 棋力业余 1~3 段、波动大：LLM 不做蒙特卡洛/深度搜索，纯靠棋感选点
- 依赖 API 网络：延迟受网络影响，调用失败时会自动 pass
- 长对局时模型可能忘记局面（受上下文窗口限制），建议 19 路对局保持在 200 手内

**后续可扩展：**
- 优化 Prompt 策略（占角、守角、死活提示）稳定棋力
- 增加对局 SGF 记录
- 增加 AI vs AI 自动对弈脚本（本地双引擎对战）
- 接入更强的模型（glm-4-plus / deepseek 等）

## 八、License

MIT
