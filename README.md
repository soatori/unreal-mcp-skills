[![skills.sh](https://skills.sh/b/soatori/unreal-mcp-skills)](https://skills.sh/soatori/unreal-mcp-skills)

# Unreal MCP Skill

Agent guidance skill for operating the Unreal Editor through Epic's official **ModelContextProtocol (MCP)** toolset.

> **Supported version:** UE 5.8+
> Learn to use this Experimental feature, but use caution when shipping with it.

## 功能说明

本技能让 AI 编程代理（Claude Code、Codex、Cursor、VS Code、Gemini CLI）能够通过 Epic 官方 MCP 协议操控 UE 编辑器，覆盖以下能力域：

### 连接与配置

- 自动检测 MCP 服务器连接状态
- 引导启用 Unreal MCP 插件、启动服务器、生成客户端配置
- 连接故障诊断：插件状态 → 服务器端点 → 配置文件 → 日志 → 工具刷新

### 编辑器控制

- 获取/设置摄像机位置与视角
- 获取当前选中的 Actor 和 Asset
- 获取 Content Browser 路径
- 检查 PIE（Play In Editor）运行状态
- 触发截图

### 场景与 Actor 管理

- 查询当前关卡信息
- 按条件搜索场景中的 Actor
- 获取 Actor 标签、变换、组件列表、包围盒
- 创建、移动、删除 Actor
- 设置 Actor 变换和选择状态

### Blueprint 操作

- 列出 Blueprint 的所有图表（Graph）
- 读取图表结构与节点信息（标题、引脚、连接关系）
- 执行 Blueprint EventGraph 逻辑分析（执行流 + 数据流）
- 通过 DSL 或节点遍历读取 Blueprint 逻辑
- 变更前自动进行只读对比检查

### 资产与内容管理

- 浏览和查询 Content Browser 中的资产
- 导入外部文件到 UE
- 保存、编译资产
- 管理材质、网格体、纹理、表格等资产类型

### 日志与诊断

- 实时读取编辑器日志（按类别和关键字过滤）
- 区分 `LogModelContextProtocol`、`LogToolsetRegistry`、`LogPython` 等日志来源
- 排除 Epic 遥测上传等无关日志干扰

### 自动化测试

- 发现和列举项目中的自动化测试
- 按需执行测试并获取结果

### Live Coding

- 触发 C++ 热重载编译
- 等待编译完成后再执行后续依赖操作

### AgentSkill 管理

- 列出和查看已有的 UE AgentSkill 资产
- 创建或更新 AgentSkill（需用户明确授权）

### 扩展工具集（可选插件）

启用 `Engine/Plugins/Experimental/Toolsets/*` 下的插件后，可解锁更多能力：

| 领域 | 可用工具集 |
|---|---|
| 插件与配置 | `PluginToolset`、`ConfigSettingsToolset` |
| 程序化生成与 VFX | `PCGToolset`、`NiagaraToolsets`、`DataflowAgent` |
| Gameplay 系统 | `GameplayTagsToolset`、`GASToolsets`、`StateTreeToolset` |
| UI 检查 | `UMGToolSet`、`MVVMToolset`、`SlateInspectorToolset` |
| 专用资产 | `PhysicsToolsets`、`AnimationAssistantToolset`、`MetaHumanGenerator` |

## 安装

```bash
npx skills add soatori/unreal-mcp-skills
```

或手动克隆：

```bash
git clone https://github.com/soatori/unreal-mcp-skills.git
```

## 快速上手

也可以使用 `/ue-mcp:` 前缀，效果相同。

### 连接配置

```
/unreal-mcp:configure <target>
```

| 参数 | 说明 | 配置格式 | 配置位置 |
|---|---|---|---|
| `claude` | 为 Claude Code 生成配置 | `.mcp.json` | 项目根目录或 `~/.claude/.mcp.json` |
| `codex` | 为 Codex 生成配置 | `.codex/config.toml` | 项目根目录 |
| `cursor` | 为 Cursor 生成配置 | `.mcp.json` | 项目根目录 |
| `vscode` | 为 VS Code 生成配置 | `.vscode/mcp.json` | 项目根目录 |
| `gemini` | 为 Gemini CLI 生成配置 | `.gemini/settings.json` | 项目根目录 |
| `all` | 为所有客户端生成配置 | — | 各自对应位置 |

执行配置时按以下流程处理：

1. **检测 UE 项目** — 若未发现 `.uproject` 文件，询问用户项目路径
2. **检查插件状态** — 检查 `ModelContextProtocol` 和 `ToolsetRegistry` 是否已启用：
   - 未启用时：询问用户是否帮忙配置（`all` 参数下自动启用）
3. **检查编辑器 MCP 设置** — 检查并配置以下关键设置：
   - Auto Start（自动启动 MCP 服务器）
   - 监听端口（默认 `8000`）
   - 其他 ModelContextProtocol 相关配置项
   - 未配置时：询问用户是否帮忙设置（`all` 参数下自动配置）
4. **检查服务器启动** — 确认服务器正在运行，未运行则引导启动
5. **生成客户端配置** — 根据目标参数生成对应配置文件
6. **连接验证** — 调用 `list_toolsets` 确认工具可用

### 编辑器操作

| 命令 | 说明 |
|---|---|
| `/unreal-mcp:execute-blueprint` | 在 UE 编辑器中执行指定 Blueprint 函数 |
| `/unreal-mcp:open-widget` | 打开 Editor Utility Widget |

### 主技能

调用 `/unreal-mcp` 时，Agent 会自动引导完成以下流程：

1. 检测 MCP 连接状态
2. 发现可用工具集（`list_toolsets`）
3. 查询工具集 schema（`describe_toolset`）
4. 安全执行编辑器操作（`call_tool`）

## Tool Search 模式

Unreal MCP 默认启用 Tool Search 模式，`tools/list` 返回三个元工具而非全部 schema：

| 元工具 | 用途 |
|---|---|
| `list_toolsets` | 列出可用 Toolset 名称和描述 |
| `describe_toolset` | 返回指定 Toolset 的工具 schema |
| `call_tool` | 调用指定 Toolset 中的工具 |

调用 `call_tool` 时需传 `toolset_name`（完整 Toolset 名）和 `tool_name`（短工具名），不要使用全限定工具名。

## 编辑器设置

| 设置项 | 默认值 | 位置 |
|---|---|---|
| Auto Start Server | `false` | Editor Preferences > General > Model Context Protocol |
| Server Port Number | `8000` | 同上 |
| Server URL Path | `/mcp` | 同上 |
| Server name | `unreal-mcp` | `serverInfo.name` |
| Enable Tool Search | `true` | `tools/list` 返回元工具 |

## 控制台命令

| 命令 | 用途 |
|---|---|
| `ModelContextProtocol.StartServer [port]` | 启动服务器，可选覆盖端口 |
| `ModelContextProtocol.StopServer` | 停止服务器并关闭会话 |
| `ModelContextProtocol.RefreshTools` | 重新加载工具注册（热重载/Game Feature 激活后使用） |
| `ModelContextProtocol.GenerateClientConfig <Client\|All>` | 生成客户端配置，支持 `ClaudeCode`、`Cursor`、`VSCode`、`Gemini`、`Codex`、`All` |

启动参数：

| 参数 | 用途 |
|---|---|
| `-ModelContextProtocolStartServer` | 启动编辑器时自动启动 MCP 服务器 |
| `-ModelContextProtocolPort=N` | 覆盖监听端口（`1..65535`） |

## 安全与限制

- Unreal MCP 为实验性功能，API 和 schema 可能变更
- 仅支持 HTTP 和 Server-Sent Events 传输，不支持 `stdio` 和 WebSocket
- 默认绑定 loopback（`127.0.0.1`），不接受非本地 Origin
- 无认证层，不要暴露到本地机器以外
- 工具调用在 Unreal 游戏线程上串行执行，不可重叠依赖调用
- PIE 运行时工具行为可能不同，结果异常时检查 PIE 状态
- 批量变更前后均应保存项目，MCP 编辑不总是可撤销的

## 自定义工具开发

支持通过 Toolset Registry 添加自定义工具：

**Python Toolset：**

```python
import unreal
import toolset_registry

@unreal.uclass()
class MyTools(unreal.ToolsetDefinition):
    @staticmethod
    @toolset_registry.tool_call
    def get_scene_info() -> dict:
        world = unreal.EditorLevelLibrary.get_editor_world()
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        return {"level_name": world.get_name(), "actor_count": len(actors)}
```

**C++ Toolset：**

- 派生自 `UToolsetDefinition`
- 标记 `UCLASS(BlueprintType, Hidden)`
- 用 `UFUNCTION(meta = (AICallable))` 暴露静态方法

创建后运行 `ModelContextProtocol.RefreshTools` 刷新注册。

## 仓库结构

```
unreal-mcp-skills/
├── SKILL.md                          # 主技能文件（Agent 加载入口）
├── skills.sh.json                    # skills.sh 发现元数据
├── agents/
│   ├── claude.md                     # Claude Code 配置说明
│   └── openai.yaml                   # Codex/OpenAI 配置说明
└── references/
    ├── mcp-tools.md                  # 完整 MCP 工具集参考文档
    └── examples/                     # 示例 MCP 配置（复制到项目根目录）
        ├── .mcp.json                 # Claude Code 配置
        ├── .cursor/mcp.json          # Cursor 配置
        ├── .codex/config.toml        # Codex 配置
        ├── .vscode/mcp.json          # VS Code 配置
        └── .gemini/settings.json     # Gemini 配置
```

## 文档

- **[SKILL.md](SKILL.md)** — 完整 Agent 指令（工作流、工具集、安全规则、调试）
- **[references/mcp-tools.md](references/mcp-tools.md)** — 安装指南、架构、工具集地图、Blueprint 手册、自定义工具开发
- **[Epic MCP 官方文档](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor)** — Unreal 官方文档
