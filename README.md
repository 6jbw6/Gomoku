# 五子棋天梯竞技平台 (Gomoku Arena)

基于 Pygame-ce 原生游戏引擎构建的高性能、现代化五子棋桌面端竞技平台（兼容 Web 网页端）。支持经典天梯排位赛、单人休闲切磋、双人面对面同屏对弈与人机启发式推演。

---

## 核心特性与设计规范

### 1. 四大核心对战模式

- 天梯排位赛 (Ranked Competitive)：
  - 采用天梯星级段位与勇者积分抵扣机制；
  - 胜场晋级升星，战败扣星，支持青铜白银保星保护与连胜额外升星。
- 单人休闲切磋 (Casual Match)：
  - 纯粹技艺推演交流，快速对局切磋，不计排位星数。
- 双人同屏对弈 (Pass-and-Play)：
  - 好友面对面轮流执子切磋交流，线下同机复刻沉香茶室博弈对决。
- 人机实战推演 (vs AI Practice)：
  - 内置多格局启发式智能棋弈算法，攻守兼备，磨砺定式与杀着招法。

---

### 2. 天梯星级段位与勇者积分体系

系统采用经典竞技段位阶梯算法，统一以【天梯排位 / 棋弈竞技】呈现：

| 段位名称 | 阶层与小段位 | 每小段升星所需 | 勇者积分上限 (保星/升星阈值) | 保星机制 |
| :--- | :--- | :---: | :---: | :--- |
| 倔强青铜 | 青铜 III → II → I | 3 星 | 100 分 | 青铜对局失败绝不掉星 |
| 秩序白银 | 白银 III → II → I | 3 星 | 120 分 | 0 星失败仅掉当前小段，不跌入青铜 |
| 荣耀黄金 | 黄金 IV → III → II → I | 4 星 | 150 分 | 触发掉段保护与勇者积分抵扣 |
| 尊贵铂金 | 铂金 IV → III → II → I | 4 星 | 200 分 | 触发勇者积分抵扣 |
| 永恒钻石 | 钻石 V → IV → III → II → I | 5 星 | 300 分 | 高阶博弈，触发勇者积分抵扣 |
| 至尊星耀 | 星耀 V → IV → III → II → I | 5 星 | 300 分 | 顶尖高手对决 |
| 最强王者 | 0 ~ 24 星 | 累积星数 | 400 分 | 星数全服实时排行榜排位 |
| 荣耀王者 | 25 ~ 49 星 | 荣耀称号 | 400 分 | 荣耀殿堂棋手 |
| 传奇王者 | 50 ~ 99 星 | 传奇称号 | 400 分 | 棋道宗师 |
| 绝世王者 | 100+ 星 | 绝世之巅 | 400 分 | 天梯巅峰第一梯队 |

- 勇者积分机制：
  - 完赛奖励：基础 +10 分；获胜额外 +15 分；
  - 连胜加成：2连胜 +10分，3连胜 +20分，4连胜及以上 +30分；
  - 焦灼局（手数 ≥ 60 手）：鼓励加分 +5 分；
  - 保星抵扣：战败扣星时，若积分达到阈值，自动消耗积分并免疫本次掉星；
  - 满额升星：积分满额且当局获胜时，扣除阈值积分并额外赠送 1 颗星！

---

### 3. 视觉与色彩规范

系统全栈践行“东方金石雅韵与温润沉香木”视觉设计：

- 沉浸式主题背景：沉香文人茶室对弈雅境 (`gomoku/web/assets/theme_bg.jpg`)，硬件加速独立层与高透滤镜增益；
- 界面质感：核心卡片、导航栏与弹窗采用高质感毛玻璃半透层 (`COLOR_CARD_BG` / `backdrop-filter`)；
- 棋盘主体：沉香金木暖纹理 (`#DDB26F` / `COLOR_BOARD_BG`)；
- 背景与卡片：玄武岩暖炭黑 (`COLOR_BG_DARK`) 与沉檀木深褐 (`COLOR_PANEL_BG`)；
- 黑子（墨石）：墨玉黑曜石立体渐变与漫反射高光；
- 白子（白玉）：羊脂温润白玉立体渐变与弧面反光；
- 核心按钮与徽章：帝王琥珀金 (`COLOR_GOLD_PRIMARY`)；
- 警示与最后手印章：朱砂印章红 (`COLOR_RED_CRIMSON`)；
- 准备就绪：竹青翡翠绿 (`COLOR_GREEN_JADE`)；
- 视觉风格：整体色调典雅沉稳，营造传统弈棋专注雅致的对弈意境。

---

### 4. 软件架构设计与 SOLID 原则落地

```text
gomoku/
├── core/             # [领域核心层] - 纯数学与状态无外部依赖 (SRP / 纯函数)
│   ├── board.py      # 15x15 棋盘二维矩阵状态与落子快照
│   ├── constants.py  # 规格常量与 (dx, dy) 连珠方向向量
│   ├── enums.py      # 棋子颜色、游戏模式、对局状态、段位枚举
│   └── rules.py      # IRuleEngine 接口, StandardRuleEngine (纯函数判定)
├── gui/              # [桌面表现层] - 原生 Pygame 桌面图形客户端
│   ├── app.py        # 桌面端总控类与 60 FPS 主循环
│   ├── scenes.py     # 大厅场景与核心对弈场景
│   ├── board_view.py # 15x15 棋盘渲染视口与坐标吸附
│   ├── components.py # 国风金石按钮、卡片、进度条与居中弹窗
│   ├── audio.py      # 声波物理合成与落子音效
│   ├── ai.py         # 启发式多格局评估引擎
│   ├── profile.py    # 本地棋手档案与段位换算持久化
│   └── constants.py  # 东方金石配色体系与规格常量
├── services/         # [应用业务层] - 调度用例与算法 (OCP / LSP / ISP)
│   ├── rank_service.py   # 天梯段位换算、升星、掉星与勇者积分算法
│   ├── room_service.py   # 房间生命周期状态机与落子分发
│   └── match_service.py  # 休闲与排位双池匹配调度器
├── storage/          # [基础设施持久层] - 仓储接口 (DIP)
│   ├── database.py       # SQLAlchemy 2.0 异步引擎与 aiosqlite
│   ├── models.py         # UserModel 与 MatchRecordModel ORM 实体
│   └── repositories.py   # IUserRepository 抽象接口与异步实现
├── api/              # [传输接入层] - HTTP / WebSocket API
│   ├── deps.py           # JWT 鉴权依赖注入与密码散列
│   ├── schemas.py        # Pydantic 强类型请求/响应校验协议
│   ├── routes_auth.py    # 游客快捷免密登录、正式用户注册登录
│   ├── routes_rank.py    # 天梯榜单拉取、好友房间创建
│   └── ws_handler.py     # WebSocket 实时双向帧长连接分发总线
└── web/              # [网页表现层] - 现代轻量自适应 Web 客户端
    ├── index.html        # 单页面主界面
    ├── css/style.css     # 东方暖木金石精修配色与毛玻璃样式表
    ├── assets/
    │   └── theme_bg.jpg  # 沉香茶室山水雅境高清主题背景图
    └── js/               # Web 端交互脚本库
```

---

## 技术选型

- 原生桌面游戏引擎：`Pygame-ce >= 2.5.0`（SDL 2.32.10，硬件加速渲染）
- 异步 Web 核心：`FastAPI >= 0.110.0`
- ASGI 服务器：`Uvicorn >= 0.28.0`
- 实时双向帧通信：`WebSockets >= 12.0`
- ORM 与持久化：`SQLAlchemy 2.0 (Async)` + `aiosqlite`
- 数据结构强校验：`Pydantic v2`
- 安全与会话：`PyJWT` + `PassLib (Bcrypt)`

---

## 全流程操作记录与 Git 分支及 Tag 规范

本项目严格遵循“日常在 dev 开发、验证后合入 main、全流程操作必记录、文档必同步、推送必带 Tag”的企业级作业标准：

- 双分支协同模型 (`main` + `dev`)：
  - `main` 分支：生产稳定主干，仅用于接收经过充分测试的 `dev` 合并，所有版本 Tag 均打在 `main` 上。
  - `dev` 分支：日常开发分支，所有编码、Bug 修复、静态检查与单元测试均在 `dev` 分支上闭环完成。
- 全流程操作履历：详见 [OPERATIONS.md](./OPERATIONS.md)，记录了从项目初始化、前端 Canvas 绘制、双向通信、异常修复、AI 清理、天梯榜单过滤到分支流转规范的全部操作日志。
- 语义化版本 Tag 体系：每一次功能发布或缺陷修复，均打上标准 SemVer 标签（如 `v1.0.0` ~ `v1.1.0`），合并到 `main` 后通过 `git push origin main --tags` 推送至远端代码托管仓库。
- 开发与运维 5 步标准作业规程 (SOP)：
  1. 切至 `dev` 分支（`git checkout dev && git merge main`）进行编码与缺陷修复；
  2. 执行 PEP 8 检测（`flake8 gomoku tests desktop_app.py run.py --max-line-length=100`）与全量测试（`pytest tests -v`）；
  3. 更新 [OPERATIONS.md](./OPERATIONS.md)（递增 Tag）与 [README.md](./README.md)；
  4. 提交并推送到 `dev` 分支（`git commit && git push origin dev`）；
  5. 切回 `main` 主干合并 `dev`（`git checkout main && git merge --no-ff dev`），签署语义化版本 Tag 并推送到远端（`git push origin main --tags`）。

---

## 快速启动与体验

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 执行自动化测试与规范检测

```bash
# 执行全部单元测试与集成测试（桌面客户端、核心规则、AI判定、段位系统、API测试）
python -m pytest tests -v

# 执行 PEP 8 语法规范静态检测（零告警通过，单行长度 ≤ 100）
flake8 gomoku tests desktop_app.py run.py --max-line-length=100
```

### 3. 启动桌面端原生游戏（默认模式）

```bash
python run.py
# 或直接执行：python desktop_app.py
```

终端将启动 1200×800 高清分辨率的东方雅韵五子棋桌面应用：
- **四大对弈模式**：天梯排位赛、休闲匹配赛、本地双人同屏对弈、人机智能切磋；
- **智能落子音效**：数学正弦波物理拟真合成落子“嗒”与按键清脆声，无外部音频资源依赖；
- **纯正棋客榜**：大厅右侧常驻棋客天梯榜，实时展示段位、胜率与天梯星星；
- **本地数据自闭环**：胜负自动结算并实时更新 `gomoku_profile.json`。

### 4. （可选）启动 Web 端在线服务

```bash
python run.py --web
```

启动后在浏览器打开 `http://127.0.0.1:8088` 即可体验 Web 版双人在线对弈与房间匹配。
