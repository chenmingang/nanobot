---
name: code-assistant
description: 独立编码助手能力。在用户需要代码分析、重构、生成、文档、修 Bug 或多文件操作时使用。主要支持 Java、Python、前端（JavaScript/TypeScript/HTML/CSS/Vue/React）。提供脚本与工作流指引，供 Agent 调用。
# 可选：取消下一行注释并设为 true，可在每次对话时自动注入本 Skill 全文
# always: true
---

# Code Assistant Skill（独立编码助手）

本 Skill 为**独立编码助手**提供统一的代码分析、重构、生成与文档能力（非 Cursor 等编辑器附属）。Agent 通过执行 `scripts/` 下脚本或按工作流直接编辑代码完成任务。

## 支持语言（优先级）

| 语言/栈 | 说明 |
|--------|------|
| **Java** | .java；类/接口/方法、JUnit、Maven 常见结构 |
| **Python** | .py；函数/类、unittest、常见风格 |
| **前端** | .js / .ts / .html / .css / .vue / .jsx / .tsx；组件、样式、脚本 |

其他语言（.go、.rs 等）仅做基础识别与通用规则，不做深度优化。

## 核心能力

1. **代码分析与理解**：结构、复杂度、导入、函数/类/接口、潜在问题（TODO、调试输出、过长行等）
2. **代码生成**：Java/Python/前端模板（类、方法、测试、组件骨架）
3. **代码重构**：重命名、提取方法、删除调试/死代码（支持多语言注释与语法）
4. **文档**：从源码生成概览文档（导入、类、方法、TODO 等）
5. **可选**：网页截图（Playwright），用于前端界面确认

## 工作流（Agent 使用方式）

### 分析优先
1. 理解用户目标（需求/ Bug/ 重构范围）
2. 需要结构化信息时：运行 `scripts/code_analyzer.py <文件或目录>`，获取 JSON
3. 根据分析结果决定：调用重构/生成脚本，或直接编辑文件

### 重构
1. 重命名：`code_refactor.py rename <文件> <旧名> <新名>`
2. 提取方法：`code_refactor.py extract-method <文件> <起始行> <结束行> <方法名>`（脚本会按扩展名推断语言）
3. 删除调试/死代码：`code_refactor.py remove-dead-code <文件>`

### 生成
1. 用 `code_generator.py` 生成样板（见下方命令），或根据上下文直接写代码
2. 将生成内容写入目标文件或粘贴到合适位置

### 修 Bug
1. 复现/定位（可配合 code_analyzer 看结构与问题列表）
2. 小步修改并验证；必要时用 refactor 做重命名/提取

## 脚本说明与用法

脚本位于 **`scripts/`** 目录，需在技能根目录或指定路径下执行（`python scripts/xxx.py` 或 `python /path/to/scripts/xxx.py`）。

### code_analyzer.py

- **作用**：单文件或整个项目分析，输出 JSON（语言、行数、复杂度、问题、导入、函数、类/接口）。
- **支持**：Java、Python、JS/TS、HTML/CSS 等；注释支持 `#`、`//`、`/* */`；Java/前端方法、类、接口会单独识别。

```bash
# 单文件
python scripts/code_analyzer.py <文件路径>

# 整个项目
python scripts/code_analyzer.py <项目目录>
```

### code_refactor.py

- **作用**：重命名、按行提取方法、删除调试/死代码；自动备份为 `<文件>.backup`。
- **支持**：Python、Java、JavaScript/TypeScript（提取方法时按扩展名生成对应语法）；删除 `print`/`System.out.println`/`console.log` 等。

```bash
python scripts/code_refactor.py rename <文件> <旧标识符> <新标识符>
python scripts/code_refactor.py extract-method <文件> <起始行> <结束行> <方法名>
python scripts/code_refactor.py remove-dead-code <文件>
```

### code_generator.py

- **作用**：生成 Java/Python/前端样板与文档骨架。
- **支持**：Java 类/方法/JUnit、Python 类/函数/unittest、JS/TS 函数/接口、HTML 模板、React 函数组件等。

```bash
# Python
python scripts/code_generator.py class <类名> [docstring] [属性...]
python scripts/code_generator.py function <函数名> [参数...]
python scripts/code_generator.py test <模块名> <被测目标>

# Java
python scripts/code_generator.py java-class <类名> [包名]
python scripts/code_generator.py java-test <被测类名> [包名]

# 前端
python scripts/code_generator.py react-component <组件名>
python scripts/code_generator.py ts-interface <接口名> [属性列表...]

# 文档（任意支持语言）
python scripts/code_generator.py docs <文件路径>

# 从模板创建文件（模板名见下方）
python scripts/code_generator.py template <模板类型> <输出路径> [key=value ...]
```

常用模板类型：`python_class`、`python_function`、`python_test`、`java_class`、`java_test`、`javascript_function`、`typescript_interface`、`react_component`、`html_template`。

### screenshot_optimizer.py（可选）

- **作用**：对给定 URL 截图（Playwright），用于前端页面确认。
- 需要安装：`playwright` 并执行 `playwright install`。

```bash
python scripts/screenshot_optimizer.py <URL> <输出图片路径> [--wait 秒] [--retry 次数]
```

## Agent 使用建议

1. **先分析再动刀**：不确定结构时先跑 `code_analyzer.py`，再决定用脚本还是直接改。
2. **语言匹配**：生成/重构时明确是 Java、Python 还是前端，选用对应命令或模板。
3. **备份与回滚**：refactor 脚本会生成 `.backup`；若 Agent 直接改文件，可提示用户用版本控制。
4. **测试**：生成或重构后建议运行项目测试或相关命令（如 `mvn test`、`pytest`、`npm test`）。
5. **解释**：完成后用一两句话说明做了什么、涉及哪些文件。
