# PaperQA2

<!-- pyml disable-num-lines 6 line-length -->

[![GitHub](https://img.shields.io/badge/GitHub-black?logo=github&logoColor=white)](https://github.com/Future-House/paper-qa)
[![PyPI version](https://badge.fury.io/py/paper-qa.svg)](https://badge.fury.io/py/paper-qa)
[![tests](https://github.com/Future-House/paper-qa/actions/workflows/tests.yml/badge.svg)](https://github.com/Future-House/paper-qa)
![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)
![PyPI Python Versions](https://img.shields.io/pypi/pyversions/paper-qa)

PaperQA2 是一个用于对 PDF、文本文件、Microsoft Office 文档和源代码文件进行高精度检索增强生成（RAG）的工具包，
重点关注科学文献。
请参阅我们最近的 [2024 年论文](https://paper.wikicrow.ai)，
了解 PaperQA2 在科学任务（如问答、摘要和矛盾检测）方面超越人类水平的性能示例。

<!--TOC-->

---

**目录**

- [快速开始](#快速开始)
  - [示例输出](#示例输出)
- [什么是 PaperQA2](#什么是-paperqa2)
  - [PaperQA2 与 PaperQA 的对比](#paperqa2-与-paperqa-的对比)
  - [PaperQA2 于 2025 年 12 月采用 CalVer 版本管理](#paperqa2-于-2025-年-12-月采用-calver-版本管理)
  - [版本 5（又称 PaperQA2）的新功能](#版本-5又称-paperqa2-的新功能)
  - [2025 年 12 月的新功能](#2025-年-12-月的新功能)
  - [PaperQA2 算法](#paperqa2-算法)
- [安装](#安装)
- [命令行使用](#命令行使用)
  - [预置配置](#预置配置)
  - [速率限制](#速率限制)
- [库使用](#库使用)
  - [智能添加/查询文档](#智能添加查询文档)
  - [手动（无代理）添加/查询文档](#手动无代理添加查询文档)
  - [异步](#异步)
  - [选择模型](#选择模型)
    - [本地托管](#本地托管)
  - [嵌入模型](#嵌入模型)
    - [指定嵌入模型](#指定嵌入模型)
    - [本地嵌入模型（Sentence Transformers）](#本地嵌入模型sentence-transformers)
  - [调整来源数量](#调整来源数量)
  - [使用代码或 HTML](#使用代码或-html)
  - [多模态支持](#多模态支持)
  - [使用外部数据库/向量数据库和缓存](#使用外部数据库向量数据库和缓存)
  - [创建索引](#创建索引)
    - [清单文件](#清单文件)
  - [复用索引](#复用索引)
  - [直接使用客户端](#直接使用客户端)
- [配置速查表](#配置速查表)
- [如何获取论文？](#如何获取论文)
- [回调函数](#回调函数)
  - [缓存嵌入](#缓存嵌入)
- [自定义提示词](#自定义提示词)
  - [前置和后置提示词](#前置和后置提示词)
- [常见问题](#常见问题)
  - [为什么我的结果与论文中的不同？](#为什么我的结果与论文中的不同)
  - [这与 LlamaIndex 或 LangChain 有什么不同？](#这与-llamaindex-或-langchain-有什么不同)
  - [可以保存或加载吗？](#可以保存或加载吗)
- [复现](#复现)
- [引用](#引用)

---

<!--TOC-->

## 快速开始

在这个示例中，我们从一个研究论文 PDF 文件夹开始，
自动获取它们的元数据——包括带有撤稿检查的引用计数，
然后将 PDF 解析并缓存到全文搜索索引中，
最后使用 LLM 代理回答用户问题。

```bash
pip install paper-qa
mkdir my_papers
curl -o my_papers/PaperQA2.pdf https://arxiv.org/pdf/2409.13740
cd my_papers
pqa ask '什么是 PaperQA2？'
```

### 示例输出

**问题：** 是否有人设计过使用蛋白质或 DNA 进行计算的神经网络？

> 多个来源支持神经网络已被设计为使用 DNA 进行计算这一说法。
> Qian、Winfree 和 Bruck 的研究表明，利用 DNA 链置换级联来构建神经网络组件，
> 如人工神经元和联想记忆，使用基于 DNA 的系统（Qian2011Neural 第 1-2 页，Qian2011Neural 第 15-16 页，Qian2011Neural 第 54-56 页）。
> 该研究包括实现 3 位 XOR 门和四神经元 Hopfield 联想记忆，
> 展示了 DNA 用于神经网络计算的潜力。
> 此外，深度学习技术在基因组学中的应用，
> 即涉及 DNA 序列的计算，已有充分记录。
> 研究已将卷积神经网络（CNN）应用于预测基因组特征，如
> 转录因子结合和 DNA 可及性（Eraslan2019Deep 第 4-5 页，Eraslan2019Deep 第 5-6 页）。
> 这些模型利用 DNA 序列作为输入数据，
> 有效地使用神经网络进行 DNA 计算。
> 虽然提供的摘录没有明确提及基于蛋白质的神经网络计算，
> 但它们强调了神经网络在蛋白质序列相关任务中的应用，
> 如预测 DNA-蛋白质结合（Zeng2016Convolutional 第 1-2 页）。
> 然而，主要关注点仍然是基于 DNA 的计算。

## 什么是 PaperQA2

PaperQA2 旨在成为处理科学论文的最佳智能 RAG 模型。
以下是一些特点：

- 简单易用的接口，提供带有文中引用的可靠回答
- 先进的实现，包括文档元数据感知嵌入
  以及基于 LLM 的重排序和上下文摘要（RCS）
- 支持智能 RAG，语言代理可以迭代优化查询和回答
- 自动冗余获取论文元数据，
  包括来自多个提供商的引用和期刊质量数据
- 适用于本地 PDF/文本文件仓库的可用全文搜索引擎
- 强大的自定义接口，默认支持所有 [LiteLLM][LiteLLM providers] 模型

[LiteLLM providers]: https://docs.litellm.ai/docs/providers
[LiteLLM general docs]: https://docs.litellm.ai/docs/

默认情况下，它使用 [OpenAI 嵌入](https://platform.openai.com/docs/guides/embeddings)
和 [模型](https://platform.openai.com/docs/models) 以及 Numpy 向量数据库来嵌入和搜索文档。
但是，您可以轻松使用其他闭源、开源模型或嵌入（见下文详情）。

PaperQA2 依赖于一些出色的库/API，使我们的项目成为可能。
以下是一些（排名不分先后）：

1. [Semantic Scholar](https://www.semanticscholar.org/)
2. [Crossref](https://www.crossref.org/)
3. [Unpaywall](https://unpaywall.org/)
4. [Pydantic](https://docs.pydantic.dev/latest/)
5. [tantivy](https://github.com/quickwit-oss/tantivy)
6. [LiteLLM][LiteLLM general docs]
7. [pybtex](https://pybtex.org/)

### PaperQA2 与 PaperQA 的对比

我们一直在努力进行基础升级，
直到 [2025 年 12 月](#paperqa2-于-2025-年-12-月采用-calver-版本管理) 之前基本遵循 [SemVer](https://semver.org/)。
这意味着我们在每次破坏性更改时会增加主版本号。
这使我们达到了当前的主版本号 v5。
那么为什么这个仓库现在叫 PaperQA2？
我们想表明，尽管我们已经
在 [许多重要指标](https://paper.wikicrow.ai) 上超越了人类性能。
所以我们随意地将版本 5 及之后称为 PaperQA2，
而之前的版本称为 PaperQA1，以表示性能的显著变化。
我们认识到 FutureHouse 在命名和计数方面存在挑战，
因此我们保留随时随意将名称更改为 PaperCrow 的权利。

### PaperQA2 于 2025 年 12 月采用 CalVer 版本管理

在 2025 年 12 月之前，我们使用 [语义版本控制](https://semver.org/)。
这最终导致了两方面的混淆：

1. 开发者：我们应该基于
   设置还是基础系统能力来增加主版本号？
   如果错误修复需要对代理行为进行破坏性更改怎么办？
2. 术语使用：我们应该使用出版物中的术语
   （例如 [PaperQA1](https://arxiv.org/abs/2312.07559)，
   [PaperQA2](https://arxiv.org/abs/2409.13740)）
   还是这个仓库/包的 Git 标签（例如 v5）？
   当有人说 "PaperQA" 时——他们指的是哪个版本？

为解决这些混淆，在 2025 年 12 月，
我们转向了[日历版本控制](https://calver.org/)。
开发者的负担减少了，因为
我们基本上取消了跨版本向后兼容的保证
（因为 CalVer 是绑定到日期的 [ZeroVer](https://0ver.org/)）。
它解决了"术语使用"问题，因为 Git 标签现在
与出版物术语完全不同（例如 PaperQA2 与 `v2025.12.17`）。
当有人说 "PaperQA" 时，它将只指系统本身，
而不是特定的代理行为快照。
当有人说 "PaperQA2" 时，它指的是 `paper-qa>=5`，
这适用于 SemVer 标签 `v5.0.0` 和新的 CalVer 标签 `v2025.12.17`。

此切换对于版本 5 的 SemVer 向后兼容，
因为 2025 年严格大于主版本 5。

### 版本 5（又称 PaperQA2）的新功能

版本 5 新增：

- 命令行工具 `pqa`
- 调用工具进行
  论文搜索、收集证据和生成答案的智能工作流
- 大幅减少了 `Docs` 对象的状态性
- 迁移到 LiteLLM 以兼容多种 LLM 提供商
  以及集中式速率限制和成本跟踪
- 一组预置配置（阅读[此部分](#预置配置)）
  包含已知的良好超参数

请注意，从早期版本的 `PaperQA` 序列化的 `Docs` 对象与版本 5 不兼容，
需要重新构建。
此外，我们的最低 Python 版本已提高到 Python 3.11。

### 2025 年 12 月的新功能

自版本 `5.29.1` 以来的最后四个月发生了许多变化：

- 新模态：表格、图形、非英语语言、数学公式
- 更多和更好的阅读器
  - 两个新的基于模型的 PDF 阅读器：[Docling](packages/paper-qa-docling)
    和 [Nvidia nemotron-parse](packages/paper-qa-nemotron)
  - 所有 PDF 阅读器现在可以解析图像和表格、报告页码、支持 DPI
  - Microsoft Office 数据类型的阅读器
- 多模态上下文摘要
  - 在创建时，媒体对象也会传递给 `summary_llm`
  - 媒体对象的嵌入空间使用 `enrichment_llm` 提示词增强
- 更简单和高效的 HTTP 栈
  - 从 `aiohttp` 和 `httpx` 合并到仅使用 `httpx`
  - 与 [`httpx-aiohttp`](https://github.com/karpetrosyan/httpx-aiohttp) 集成以提高性能
- `Context` 相关性简化并移除了一些假设
- 许多小功能，例如
  在无效 JSON 时重试 `Context` 创建、
  兼容 2025 年秋季的前沿 LLM、
  以及改进的提示词模板
- 通过 Semantic Scholar 和 OpenAlex 修复元数据处理中的多个问题，
  以及元数据处理
  （例如错误推断主文本和 SI 的相同文档 ID）
- 完成了过去一年积累的弃用

### PaperQA2 算法

要理解 PaperQA2，让我们从底层算法的各个部分开始。
PaperQA2 的默认工作流程如下：

| 阶段                  | PaperQA2 操作                                                                                  |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| **1. 论文搜索**    | - 从 LLM 生成的关键词查询中获取候选论文                                    |
|                        | - 对候选论文进行分块、嵌入并添加到状态                                     |
| **2. 收集证据** | - 将查询嵌入到向量中                                              |
|                        | - 在当前状态中对 top _k_ 文档块进行排名                           |
|                        | - 在当前查询的上下文中为每个块创建评分摘要           |
|                        | - 使用 LLM 重新评分并选择最相关的摘要               |
| **3. 生成答案** | - 将最佳摘要与上下文一起放入提示词                       |
|                        | - 使用提示词生成答案                                              |

语言代理可以以任何顺序调用这些工具。
例如，LLM 代理可能进行狭窄和广泛的搜索，
或在收集证据步骤和生成答案步骤中使用不同的表述。

## 安装

对于非开发环境设置，
从 [PyPI](https://pypi.org/project/paper-qa/) 安装 PaperQA2（即版本 5）。
请注意，版本 5 需要 Python 3.11+。

```bash
pip install paper-qa>=5
```

对于开发环境设置，
请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 文件。

PaperQA2 使用 LLM 来操作，
因此您需要设置适当的 [API 密钥环境变量][LiteLLM providers]
（即 `export OPENAI_API_KEY=sk-...`）
或设置开源 LLM 服务器（即使用 [llamafile](https://github.com/Mozilla-Ocho/llamafile)）。
任何与 LiteLLM 兼容的模型都可以配置为与 PaperQA2 一起使用。

如果您需要索引大量论文（100+），
您可能需要同时获取
[Crossref](https://www.crossref.org/documentation/metadata-plus/metadata-plus-keys/)
和 [Semantic Scholar](https://www.semanticscholar.org/product/api#api-key)
的 API 密钥，
这将允许您避免触及这些元数据服务的公共速率限制。
这些可以作为 `CROSSREF_API_KEY` 和 `SEMANTIC_SCHOLAR_API_KEY` 变量导出。

## 命令行使用

测试 PaperQA2 最快的方式是通过 CLI。首先导航到包含一些论文的目录并使用 `pqa` 命令：

```bash
pqa ask '什么是 PaperQA2？'
```

您将看到 PaperQA2 索引您的本地 PDF 文件，
为每个文件收集必要的元数据
（使用 [Crossref](https://www.crossref.org/) 和 [Semantic Scholar](https://www.semanticscholar.org/)），
搜索该索引，然后将文件分成块状证据上下文、
对其进行排名，最终生成答案。
下次查询此目录时，
您的索引已经构建好了（除了检测到的任何差异，如新增的论文），
因此它将跳过索引和分块步骤。

所有先前的答案都会被索引和存储，
您可以通过 `search` 子命令查询来查看它们，
或者在您的 `PQA_HOME` 目录中自行访问，
默认为 `~/.pqa/`。

```bash
pqa -i 'answers' search '排序和上下文摘要'
```

PaperQA2 高度可配置，从命令行运行时，
`pqa --help` 显示所有选项和简短描述。
例如，使用更高温度运行：

```bash
pqa --temperature 0.5 ask '什么是 PaperQA2？'
```

您可以使用 `pqa view` 查看所有设置。
另一个有用的功能是切换到其他模板设置——例如
`fast` 是一个更快回答的设置，
您可以使用 `pqa -s fast view` 查看它

也许您有一些想要保存的新设置？您可以这样做

```bash
pqa -s my_new_settings --temperature 0.5 --llm foo-bar-5 save
```

然后您可以这样使用它

```bash
pqa -s my_new_settings ask '什么是 PaperQA2？'
```

如果您运行 `pqa` 命令需要新的索引，
比如说您更改了默认的 chunk_size，
将自动为您创建一个新索引。

```bash
pqa --parsing.chunk_size 5000 ask '什么是 PaperQA2？'
```

您也可以使用 `pqa` 通过 search 命令进行使用 LLM 的全文搜索。
例如，让我们保存一个目录的索引并给它一个名称：

```bash
pqa -i nanomaterials index
```

现在我可以搜索关于热电材料的论文：

```bash
pqa -i nanomaterials search thermoelectrics
```

或者我可以使用正常的 ask

```bash
pqa -i nanomaterials ask '热电材料中是否存在纳米级特征？'
```

CLI 和模块都有基于先前性能和出版物的预配置设置，
可以按如下方式调用：

```bash
pqa --settings <setting name> \
    ask '热电材料中是否存在纳米级特征？'
```

### 预置配置

在 [`src/paperqa/configs`](src/paperqa/configs) 中，我们捆绑了已知有用的设置：

| 设置名称      | 描述                                                                                                              |
| ------------- | ----------------------------------------------------------------------------------------------------------------- |
| high_quality  | 高性能，相对昂贵（因为 `evidence_k` = 15）使用 `ToolSelector` 代理的查询。                                           |
| fast          | 以低成本和快速获取答案的设置。                                                                                     |
| wikicrow      | 用于模拟我们的 WikiCrow 出版物中使用的维基百科文章写作的设置。                                                     |
| contracrow    | 用于在论文中寻找矛盾的设置，您的查询应该是一个需要被标记为矛盾（或不是）的声明。                                    |
| debug         | 仅对调试有用的设置，但在任何实际应用中都无济于事。                                                                 |
| tier1_limits  | 匹配 OpenAI 每个层级的速率限制的设置，您可以使用 `tier<1-5>_limits` 指定层级。                                     |

### 速率限制

如果您遇到速率限制，例如使用 OpenAI Tier 1 计划，您可以将其添加到 PaperQA2。
对于每个 OpenAI 层级，存在一个预构建的设置来限制使用。

```bash
pqa --settings 'tier1_limits' ask '什么是 PaperQA2？'
```

这将限制您的系统使用 [tier1_limits](src/paperqa/configs/tier1_limits.json)，
并减慢您的查询以适应。

您也可以使用与 [limits](https://limits.readthedocs.io/en/stable/quickstart.html#rate-limit-string-notation) 模块中规范匹配的任意速率限制字符串手动指定：

```bash
pqa --summary_llm_config '{"rate_limit": {"gpt-4o-2024-11-20": "30000 per 1 minute"}}' \
    ask '什么是 PaperQA2？'
```

或者，如果命令式调用，添加到 `Settings` 对象中：

```python
from paperqa import Settings, ask

answer_response = ask(
    "什么是 PaperQA2？",
    settings=Settings(
        llm_config={"rate_limit": {"gpt-4o-2024-11-20": "30000 per 1 minute"}},
        summary_llm_config={"rate_limit": {"gpt-4o-2024-11-20": "30000 per 1 minute"}},
    ),
)
```

## 库使用

PaperQA2 的完整工作流程可以通过 Python 直接访问：

```python
from paperqa import Settings, ask

answer_response = ask(
    "什么是 PaperQA2？",
    settings=Settings(temperature=0.5, paper_directory="my_papers"),
)
```

请参阅我们的[安装文档](#安装)了解如何从 PyPI 安装包。

### 智能添加/查询文档

答案对象具有以下属性：
`formatted_answer`、`answer`（仅答案）、`question` 和 `context`（找到的用于回答的段落摘要）。
`ask` 将使用 `SearchPapers` 工具，该工具将查询本地文件索引，
您可以通过 `Settings` 对象指定此位置：

```python
from paperqa import Settings, ask

answer_response = ask(
    "什么是 PaperQA2？",
    settings=Settings(
        temperature=0.5, agent={"index": {"paper_directory": "my_papers"}}
    ),
)
```

`ask` 只是真正入口点的一个便捷包装器，
如果您想运行并发异步工作负载，可以访问它：

```python
from paperqa import Settings, agent_query

answer_response = await agent_query(
    query="什么是 PaperQA2？",
    settings=Settings(
        temperature=0.5, agent={"index": {"paper_directory": "my_papers"}}
    ),
)
```

默认代理将使用基于 LLM 的代理，
但您也可以指定 `"fake"` 代理来使用硬编码的调用路径
搜索 -> 收集证据 -> 回答以减少 token 使用。

### 手动（无代理）添加/查询文档

通常通过代理执行，代理调用搜索工具，
这会在幕后为您将文档添加到 `Docs` 对象。
但是，如果您更喜欢细粒度控制，
可以直接与 `Docs` 对象交互。

请注意，手动添加和查询 `Docs` 不会影响性能。
它只是删除了与代理选择要添加的文档相关的自动化。

```python
from paperqa import Docs, Settings

# 支持的扩展名包括 .pdf、.txt、.md、.html、.docx、.xlsx、.pptx 和代码文件（例如 .py、.ts、.yaml）
doc_paths = ("myfile.pdf", "myotherfile.pdf")

# 通过添加一堆文档来准备 Docs 对象
docs = Docs()
for doc_path in doc_paths:
    await docs.aadd(doc_path)

# 设置我们想要查询 Docs 对象的方式
settings = Settings()
settings.llm = "claude-3-5-sonnet-20240620"
settings.answer.answer_max_sources = 3

# 查询 Docs 对象以获取答案
session = await docs.aquery("什么是 PaperQA2？", settings=settings)
print(session)
```

### 异步

PaperQA2 被编写为异步使用。
同步 API 只是异步的包装器。
以下是方法及其 `async` 等价物：

| 同步              | 异步                |
| ----------------- | ------------------- |
| `Docs.add`        | `Docs.aadd`         |
| `Docs.add_file`   | `Docs.aadd_file`    |
| `Docs.add_url`    | `Docs.aadd_url`     |
| `Docs.get_evidence` | `Docs.aget_evidence` |
| `Docs.query`      | `Docs.aquery`       |

同步版本只是循环调用异步版本。
大多数现代 Python 环境原生支持 `async`（包括 Jupyter notebooks！）。
所以您可以在 Jupyter Notebook 中这样做：

```python
import asyncio
from paperqa import Docs


async def main() -> None:
    docs = Docs()
    # 支持的扩展名包括 .pdf、.txt、.md、.html、.docx、.xlsx、.pptx 和代码文件（例如 .py、.ts、.yaml）
    for doc in ("myfile.pdf", "myotherfile.pdf"):
        await docs.aadd(doc)

    session = await docs.aquery("什么是 PaperQA2？")
    print(session)


asyncio.run(main())
```

### 选择模型

默认情况下，PaperQA2 使用 OpenAI 的 `gpt-4o-2024-11-20` 模型作为
`summary_llm`、`llm` 和 `agent_llm`。
请参阅[配置速查表](#配置速查表)
了解更多关于这些设置的信息。
PaperQA2 还默认使用 OpenAI 的 `text-embedding-3-small` 模型作为 `embedding` 设置。
如果您没有 OpenAI API 密钥，可以使用不同的嵌入模型。
更多关于嵌入模型的信息可以在["嵌入模型"部分](#嵌入模型)找到。

我们使用 [`lmi`](https://github.com/Future-House/ldp/tree/main/packages/lmi) 包作为 LLM 接口，
它反过来使用 `litellm` 支持多种 LLM 提供商。
您可以轻松调整以使用 `litellm` 支持的任何模型：

```python
from paperqa import Settings, ask

answer_response = ask(
    "什么是 PaperQA2？",
    settings=Settings(
        llm="gpt-4o-mini", summary_llm="gpt-4o-mini", agent={"index": {"paper_directory": "my_papers"}}
    ),
)
```

要使用 Claude，请确保设置 `ANTHROPIC_API_KEY` 环境变量。
在这个例子中，我们还使用了不同的嵌入模型。
请确保 `pip install paper-qa[local]` 以使用本地嵌入模型。

```python
from paperqa import Settings, ask
from paperqa.settings import AgentSettings

answer_response = ask(
    "什么是 PaperQA2？",
    settings=Settings(
        llm="claude-3-5-sonnet-20240620",
        summary_llm="claude-3-5-sonnet-20240620",
        agent=AgentSettings(agent_llm="claude-3-5-sonnet-20240620"),
        # 参见：https://huggingface.co/sentence-transformers/multi-qa-MiniLM-L6-cos-v1
        embedding="st-multi-qa-MiniLM-L6-cos-v1",
    ),
)
```

或 Gemini，通过设置 Google AI Studio 的 `GEMINI_API_KEY`

```python
from paperqa import Settings, ask
from paperqa.settings import AgentSettings

answer_response = ask(
    "什么是 PaperQA2？",
    settings=Settings(
        llm="gemini/gemini-2.0-flash",
        summary_llm="gemini/gemini-2.0-flash",
        agent=AgentSettings(agent_llm="gemini/gemini-2.0-flash"),
        embedding="gemini/text-embedding-004",
    ),
)
```

#### 本地托管

您可以使用 llama.cpp 作为 LLM。
请注意，您应该使用相对较大的模型，
因为 PaperQA2 需要遵循大量指令。
使用 7B 模型不会获得良好的性能。

最简单的设置方法是下载一个 [llama file](https://github.com/Mozilla-Ocho/llamafile)
并使用 `-cb -np 4 -a my-llm-model --embedding` 执行它
这将启用连续批处理和嵌入。

```python
from paperqa import Settings, ask

local_llm_config = dict(
    model_list=[
        dict(
            model_name="my_llm_model",
            litellm_params=dict(
                model="my-llm-model",
                api_base="http://localhost:8080/v1",
                api_key="sk-no-key-required",
                temperature=0.1,
                frequency_penalty=1.5,
                max_tokens=512,
            ),
        )
    ]
)

answer_response = ask(
    "什么是 PaperQA2？",
    settings=Settings(
        llm="my-llm-model",
        llm_config=local_llm_config,
        summary_llm="my-llm-model",
        summary_llm_config=local_llm_config,
    ),
)
```

也支持使用 `ollama` 托管的模型。
要运行下面的示例，请确保已通过 ollama 下载 llama3.2 和 mxbai-embed-large。

```python
from paperqa import Settings, ask

local_llm_config = {
    "model_list": [
        {
            "model_name": "ollama/llama3.2",
            "litellm_params": {
                "model": "ollama/llama3.2",
                "api_base": "http://localhost:11434",
            },
        }
    ]
}

answer_response = ask(
    "什么是 PaperQA2？",
    settings=Settings(
        llm="ollama/llama3.2",
        llm_config=local_llm_config,
        summary_llm="ollama/llama3.2",
        summary_llm_config=local_llm_config,
        embedding="ollama/mxbai-embed-large",
    ),
)
```

### 嵌入模型

嵌入用于检索 k 个文本（其中 k 通过 `Settings.answer.evidence_k` 指定）
进行重排序和上下文摘要。
如果您不想使用嵌入，而只想获取所有块，
请通过 `Settings.answer.evidence_retrieval` 设置禁用"证据检索"。

PaperQA2 默认使用 OpenAI（`text-embedding-3-small`）嵌入，
但对向量存储和嵌入选择都有灵活的选项。

#### 指定嵌入模型

指定嵌入模型最简单的方法是通过 `Settings.embedding`：

```python
from paperqa import Settings, ask

answer_response = ask(
    "什么是 PaperQA2？",
    settings=Settings(embedding="text-embedding-3-large"),
)
```

`embedding` 接受 litellm 支持的任何嵌入模型名称。
PaperQA2 还支持嵌入输入 `"hybrid-<model_name>"`
即 `"hybrid-text-embedding-3-small"` 使用混合稀疏关键词（基于令牌模嵌入）
和密集向量嵌入，其中任何 litellm 模型都可用于密集模型名称。
`"sparse"` 可用于仅使用稀疏关键词嵌入。

嵌入模型用于创建 PaperQA2 的全文嵌入向量索引（`texts_index` 参数）。
嵌入模型可以在将新论文添加到 `Docs` 对象时指定为设置：

```python
from paperqa import Docs, Settings

docs = Docs()
for doc in ("myfile.pdf", "myotherfile.pdf"):
    await docs.aadd(doc, settings=Settings(embedding="text-embedding-large-3"))
```

请注意，PaperQA2 使用 Numpy 作为密集向量存储。
其使用关键词搜索初始化的设计将每个答案所需的块数量
减少到相对较小的数量 < 1k。
因此，`NumpyVectorStore` 是一个很好的起点，它是一个简单的内存存储，没有索引。
但是，如果需要大于内存的向量存储，
您可以通过 `QdrantVectorStore` 类使用外部向量数据库（如 [Qdrant](https://qdrant.tech/)）。

混合嵌入可以自定义：

```python
from paperqa import (
    Docs,
    HybridEmbeddingModel,
    SparseEmbeddingModel,
    LiteLLMEmbeddingModel,
)


model = HybridEmbeddingModel(
    models=[LiteLLMEmbeddingModel(), SparseEmbeddingModel(ndim=1024)]
)
docs = Docs()
for doc in ("myfile.pdf", "myotherfile.pdf"):
    await docs.aadd(doc, embedding_model=model)
```

稀疏嵌入（关键词）模型默认为 256 维，
但可以通过 `ndim` 参数指定。

#### 本地嵌入模型（Sentence Transformers）

如果您安装了 `sentence-transformers`，可以使用 `SentenceTransformerEmbeddingModel` 模型，
这是一个[本地嵌入库](https://sbert.net/)，支持 HuggingFace 模型等。
您可以通过添加 `local` 附加项来安装它。

```sh
pip install paper-qa[local]
```

然后使用 `st-` 前缀嵌入模型名称：

```python
from paperqa import Settings, ask

answer_response = ask(
    "什么是 PaperQA2？",
    settings=Settings(embedding="st-multi-qa-MiniLM-L6-cos-v1"),
)
```

或使用混合模型

```python
from paperqa import Settings, ask

answer_response = ask(
    "什么是 PaperQA2？",
    settings=Settings(embedding="hybrid-st-multi-qa-MiniLM-L6-cos-v1"),
)
```

### 调整来源数量

您可以调整来源（文本段落）的数量以减少 token 使用或添加更多上下文。
`k` 指的是 top k 最相关和多样化（可能来自不同来源）的段落。
每个段落都被发送到 LLM 进行摘要，或确定它是否无关。
此步骤后，应用 `max_sources` 的限制，以便最终答案可以适应 LLM 上下文窗口。
因此，`k` > `max_sources`，而 `max_sources` 是最终答案中使用的来源数量。

```python
from paperqa import Settings

settings = Settings()
settings.answer.answer_max_sources = 3
settings.answer.evidence_k = 5

await docs.aquery(
    "什么是 PaperQA2？",
    settings=settings,
)
```

### 使用代码或 HTML

您不需要使用论文——您可以使用代码或原始 HTML。
请注意，此工具专注于回答问题，
所以它在编写代码方面不会表现良好。
需要注意的是，该工具无法从代码中推断引用，
因此您需要自己提供它们。

```python
import glob
import os
from paperqa import Docs

source_files = glob.glob("**/*.js")

docs = Docs()
for f in source_files:
    # 这假设文件名在代码中是唯一的
    await docs.aadd(
        f, citation="File " + os.path.basename(f), docname=os.path.basename(f)
    )
session = await docs.aquery("标题栏中的搜索栏在哪里定义？")
print(session)
```

### 多模态支持

多模态支持包括：

- 独立图像
- PDF 中的图像或表格

`Docs` 对象通过 `ParsedMedia` 对象存储媒体。
在对文档进行分块时，媒体不会在块边界处分割，
因此 2+ 个块可能对应于同一个媒体。
这意味着在 PaperQA 中，每个块
在 `ParsedMedia` 和块之间具有一对多关系。

根据源文档，同一图像可以出现多次
（例如 PDF 的每一页边距都有一个 logo）。
因此，客户端应考虑媒体数据库
与块之间具有多对多关系。

由于 PaperQA 的证据收集过程以基于文本的检索为中心，
可能相关的图像或表格不会被检索到
因为它们关联的文本内容无关。
举一个具体的例子，想象一下论文中的图形有一个简洁的标题，
并且放在相关正文的下一页。
为了解决这个问题，PaperQA 支持在文档读取时进行媒体丰富。
基本上，在读取 PDF 后，
`parsing.enrichment_llm` 接收 `parsing.enrichment_prompt`
和同位文本，为每个图像/表格生成合成标题。
合成标题用于移动每个文本块的嵌入，
但与实际源文本分开保存。
这样，证据收集可以获取相关的图像/表格，
而不会有用 LLM 生成的标题污染上下文摘要的风险。

如果您想要多模态 PDF 阅读，但不想要丰富功能
（因为会在读取时添加一个 LLM 提示词/媒体），
可以通过将 `parsing.multimodal` 设置为 `ON_WITHOUT_ENRICHMENT` 来禁用丰富。

在为给定块（`Text`）创建上下文摘要时，
摘要 LLM 会接收块的文本和块的关联媒体，
但输出的上下文摘要本身仍然是纯文本。

如果您愿意，
将提示词 `paperqa.prompts.summary_json_multimodal_system_prompt`
指定给设置 `prompt.summary_json_system`
将包含一个 `used_images` 标志，
用于归因于任何上下文摘要中的图像使用。

### 使用外部数据库/向量数据库和缓存

您可能希望将解析的文本和嵌入缓存到外部数据库或文件中。
然后您可以直接从这些构建 Docs 对象：

```python
from paperqa import Docs, Doc, Text

docs = Docs()

for ... in my_docs:
    doc = Doc(docname=..., citation=..., dockey=..., citation=...)
    texts = [Text(text=..., name=..., doc=doc) for ... in my_texts]
    docs.add_texts(texts, doc)
```

### 创建索引

默认情况下，索引将放置在[主目录][home dir]中。
这可以通过 `PQA_HOME` 环境变量控制。

索引是通过读取 `IndexSettings.paper_directory` 中的文件来创建的。
默认情况下，我们递归读取论文目录的子目录，
除非使用 `IndexSettings.recurse_subdirectories` 禁用。
论文目录不会被修改，它只是被读取。

[home dir]: https://docs.python.org/3/library/pathlib.html#pathlib.Path.home

#### 清单文件

索引过程尝试使用 LLM 驱动的文本处理来推断论文元数据（如标题和 DOI）。
您可以使用"清单"文件避免这种不确定性，
这是一个包含 `DocDetails` 字段的 CSV（顺序无关）。
例如：

- `file_location`：论文 PDF 在索引目录中的相对路径
- `doi`：论文的 DOI
- `title`：论文的标题

通过提供这些信息，
我们确保对元数据提供商（如 Crossref）的查询是准确的。

为简化创建清单，有一个辅助类方法 `Doc.to_csv`，
当在 `DocDetails` 上调用时也可以工作。

### 复用索引

本地搜索索引是基于当前 `Settings` 对象的哈希值构建的。
因此，请确保正确指定 `IndexSettings` 对象的 `paper_directory`。
一般来说，建议：

1. 给定一文件夹论文预构建一个索引（可能需要几分钟）
2. 复用索引执行多次查询

```python
import os

from paperqa import Settings
from paperqa.agents.main import agent_query
from paperqa.agents.search import get_directory_index


async def amain(folder_of_papers: str | os.PathLike) -> None:
    settings = Settings(agent={"index": {"paper_directory": folder_of_papers}})

    # 1. 构建索引。注意，当未指定时，索引名称是自动生成的
    built_index = await get_directory_index(settings=settings)
    print(settings.get_index_name())  # 显示自动生成的索引名称
    print(await built_index.index_files)  # 显示索引内容

    # 2. 尽可能多地使用设置与 ask
    answer_response_1 = await agent_query(
        query="什么是很酷的检索增强生成技术？",
        settings=settings,
    )
    answer_response_2 = await agent_query(
        query="什么是 PaperQA2？",
        settings=settings,
    )
```

### 直接使用客户端

PaperQA2 最强大的功能之一是能够组合来自多个元数据源的数据。
例如，[Unpaywall](https://unpaywall.org/) 可以提供开放获取状态/直接 PDF 链接，
[Crossref](https://www.crossref.org/) 可以提供 bibtex，
而 [Semantic Scholar](https://www.semanticscholar.org/) 可以提供引用许可证。
以下是简短的演示：

```python
from paperqa.clients import DocMetadataClient, ALL_CLIENTS

client = DocMetadataClient(metadata_clients=ALL_CLIENTS)
details = await client.query(title="使用化学工具增强语言模型")

print(details.formatted_citation)
# Andres M. Bran, Sam Cox, Oliver Schilter, Carlo Baldassari,
# Andrew D. White, and Philippe Schwaller.
#  Augmenting large language models with chemistry tools. Nature Machine Intelligence,
# 6:525-535, May 2024. URL: https://doi.org/10.1038/s42256-024-00832-8,
# doi:10.1038/s42256-024-00832-8.
# This article has 243 citations and is from a domain leading peer-reviewed journal.

print(details.citation_count)
# 243

print(details.license)
# cc-by

print(details.pdf_url)
# https://www.nature.com/articles/s42256-024-00832-8.pdf
```

`client.query` 旨在检查标题的精确匹配。
它具有一定的鲁棒性（如大小写、漏掉一个词）。
不过标题会有重复——所以您也可以添加作者来消歧。
或者您可以直接提供 DOI `client.query(doi="10.1038/s42256-024-00832-8")`。

如果您大规模这样做，
您可能不想使用 `ALL_CLIENTS`（只需省略参数），
您可以指定您想要的特定字段以加快查询。
例如：

```python
details = await client.query(
    title="使用化学工具增强大型语言模型",
    authors=["Andres M. Bran", "Sam Cox"],
    fields=["title", "doi"],
)
```

这将比第一次查询快得多，我们将确信作者匹配。

## 配置速查表

| 设置                                              | 默认值                                     | 描述                                                                                                                              |
| ------------------------------------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `llm`                                            | `"gpt-4o-2024-11-20"`                    | 用于一般用途的 LLM，包括元数据推断（见 Docs.aadd）和答案生成（见 Docs.aquery 和 gen_answer 工具）。                               |
| `llm_config`                                     | `None`                                    | `llm` 的可选配置。                                                                                                               |
| `summary_llm`                                    | `"gpt-4o-2024-11-20"`                    | 用于创建上下文摘要的 LLM（见 Docs.aget_evidence 和 gather_evidence 工具）。                                                       |
| `summary_llm_config`                             | `None`                                    | `summary_llm` 的可选配置。                                                                                                       |
| `embedding`                                      | `"text-embedding-3-small"`               | 添加论文时嵌入文本块的嵌入模型。                                                                                                  |
| `embedding_config`                               | `None`                                    | `embedding` 的可选配置。                                                                                                         |
| `temperature`                                    | `0.0`                                     | LLM 的温度。                                                                                                                     |
| `batch_size`                                     | `1`                                       | 调用 LLM 的批量大小。                                                                                                             |
| `texts_index_mmr_lambda`                         | `1.0`                                     | 文本索引中 MMR 的 lambda 值。                                                                                                    |
| `verbosity`                                      | `0`                                       | 日志的整数详细级别（0-3）。3 = 记录所有 LLM/嵌入调用。                                                                           |
| `custom_context_serializer`                       | `None`                                    | 覆盖默认答案上下文序列化的自定义异步函数（请参见类型签名）。                                                                        |
| `answer.evidence_k`                              | `10`                                      | 要检索的证据数量。                                                                                                                |
| `answer.evidence_retrieval`                      | `True`                                    | 使用检索 vs 处理所有文档。                                                                                                        |
| `answer.evidence_summary_length`                 | `"about 100 words"`                      | 证据摘要的长度。                                                                                                                  |
| `answer.evidence_skip_summary`                   | `False`                                   | 是否跳过摘要。                                                                                                                   |
| `answer.evidence_text_only_fallback`             | `False`                                   | 是否允许在不存在媒体的情况下重试上下文创建。                                                                                      |
| `answer.answer_max_sources`                      | `5`                                       | 答案的最大来源数。                                                                                                                |
| `answer.max_answer_attempts`                     | `None`                                    | 生成答案的最大尝试次数。                                                                                                          |
| `answer.answer_length`                           | `"about 200 words, but can be longer"` | 最终答案的长度。                                                                                                                  |
| `answer.max_concurrent_requests`                 | `4`                                       | LLM 的最大并发请求数。                                                                                                            |
| `answer.answer_filter_extra_background`          | `False`                                   | 是否引用模型中的背景信息。                                                                                                        |
| `answer.get_evidence_if_no_contexts`            | `True`                                    | 允许延迟证据收集。                                                                                                                |
| `answer.group_contexts_by_question`              | `False`                                   | 在最终上下文提示中按底层 `gather_evidence` 问题对最终上下文进行分组。                                                              |
| `answer.evidence_relevance_score_cutoff`         | `1`                                       | 包含在答案上下文中的证据相关性评分截止值（inclusive）                                                                              |
| `answer.skip_evidence_citation_strip`            | `False`                                   | 跳过从 `gather_evidence` 上下文中移除引用                                                                                        |
| `parsing.page_size_limit`                        | `1,280,000`                               | 每页字符限制。                                                                                                                    |
| `parsing.use_doc_details`                        | `True`                                    | 是否获取文档的元数据详情。                                                                                                        |
| `parsing.reader_config`                          | `dict`                                    | 文档阅读器的可选关键字参数。                                                                                                      |
| `parsing.multimodal`                             | `True`                                    | 控制从适用文档中解析文本和媒体，以及可能用文本描述丰富它们。                                                                        |
| `parsing.defer_embedding`                        | `False`                                   | 是否延迟嵌入直到摘要。                                                                                                            |
| `parsing.parse_pdf`                              | `paperqa_pypdf.parse_pdf_to_pages`        | 解析 PDF 文件的函数。                                                                                                             |
| `parsing.configure_pdf_parser`                   | No-op                                     | 在 `parse_pdf` 中配置 PDF 解析器的可调用对象，对于启用日志记录等行为很有用。                                                       |
| `parsing.doc_filters`                            | `None`                                    | 允许文档的可选过滤器。                                                                                                            |
| `parsing.use_human_readable_clinical_trials`     | `False`                                   | 将临床试验 JSON 解析为可读文本。                                                                                                  |
| `parsing.enrichment_llm`                         | `"gpt-4o-2024-11-20"`                    | 媒体丰富的 LLM。                                                                                                                  |
| `parsing.enrichment_llm_config`                  | `None`                                    | `enrichment_llm` 的可选配置。                                                                                                    |
| `parsing.enrichment_page_radius`                 | `1`                                       | 丰富中上下文文本的页半径。                                                                                                        |
| `parsing.enrichment_prompt`                      | `image_enrichment_prompt_template`        | 丰富媒体的提示模板。                                                                                                              |
| `parsing.citation_prompt`                        | `citation_prompt`                         | 从查看一个块创建引用的提示。                                                                                                      |
| `parsing.structured_citation_prompt`             | `structured_citation_prompt`              | 从查看一个块创建引用（在 JSON 中）的提示。                                                                                         |
| `parsing.disable_doc_valid_check`                | `False`                                   | 禁用检查文档是否看起来像文本（解析正确）的标志。                                                                                    |
| `prompts.summary`                                | `summary_prompt`                          | 总结文本的模板，必须包含匹配 `summary_prompt` 的变量。                                                                            |
| `prompts.qa`                                     | `qa_prompt`                               | QA 的模板，必须包含匹配 `qa_prompt` 的变量。                                                                                      |
| `prompts.select`                                 | `select_paper_prompt`                     | 选择论文的模板，必须包含匹配 `select_paper_prompt` 的变量。                                                                        |
| `prompts.pre`                                    | `None`                                    | 可选的前置提示词，用原始问题作为模板，在 QA 提示词之前追加信息。                                                                   |
| `prompts.post`                                   | `None`                                    | 可选的后处理提示词，可以访问 PQASession 字段。                                                                                    |
| `prompts.system`                                 | `default_system_prompt`                   | 模型的系统提示。                                                                                                                  |
| `prompts.use_json`                               | `True`                                    | 是否使用 JSON 格式化。                                                                                                            |
| `prompts.summary_json`                           | `summary_json_prompt`                     | JSON 特定的摘要提示。                                                                                                             |
| `prompts.summary_json_system`                    | `summary_json_system_prompt`              | JSON 摘要的系统提示。                                                                                                             |
| `prompts.context_outer`                          | `CONTEXT_OUTER_PROMPT`                    | 有关如何在生成答案中格式化所有上下文的提示。                                                                                        |
| `prompts.context_inner`                          | `CONTEXT_INNER_PROMPT`                   | 有关在生成答案中格式化单个上下文的提示。必须包含 'name' 和 'text' 变量。                                                          |
| `prompts.answer_iteration_prompt`               | `answer_iteration_prompt_template`        | 注入现有先前答案以允许迭代的提示。默认不注入先前答案。                                                                              |
| `agent.agent_llm`                                | `"gpt-4o-2024-11-20"`                    | 代理内进行工具选择的 LLM。                                                                                                        |
| `agent.agent_llm_config`                         | `None`                                    | `agent_llm` 的可选配置。                                                                                                          |
| `agent.agent_type`                              | `"ToolSelector"`                          | 要使用的代理类型。                                                                                                                |
| `agent.agent_config`                             | `None`                                    | AGENT 构造函数的可选 kwarg。                                                                                                      |
| `agent.agent_system_prompt`                      | `env_system_prompt`                       | 可选的系统提示消息。                                                                                                              |
| `agent.agent_prompt`                             | `env_reset_prompt`                        | 代理提示。                                                                                                                        |
| `agent.return_paper_metadata`                    | `False`                                   | 是否在搜索工具结果中包含论文标题/年份。                                                                                            |
| `agent.search_count`                             | `8`                                       | 搜索计数。                                                                                                                        |
| `agent.timeout`                                  | `500.0`                                   | 代理执行超时（秒）。                                                                                                              |
| `agent.tool_names`                              | `None`                                    | 提供给代理的工具的可选覆盖。                                                                                                      |
| `agent.max_timesteps`                           | `None`                                    | 环境步骤的可选上限。                                                                                                              |
| `agent.agent_evidence_n`                         | `1`                                       | 收集证据后显示给代理的 top n 排名证据。                                                                                            |
| `agent.rebuild_index`                           | `True`                                    | 在代理运行器开始时重建索引的标志。                                                                                                 |
| `agent.callbacks`                               | `{}`                                      | 使用环境状态调用的命名可调用函数列表。                                                                                              |
| `agent.index.name`                              | `None`                                    | 索引的可选名称。                                                                                                                  |
| `agent.index.paper_directory`                   | `当前工作目录`                            | 要索引的论文所在目录。                                                                                                             |
| `agent.index.manifest_file`                     | `None`                                    | 包含文档属性的清单 CSV 路径。                                                                                                      |
| `agent.index.index_directory`                   | `pqa_directory("indexes")`               | 存储 PQA 索引的目录。                                                                                                             |
| `agent.index.use_absolute_paper_directory`       | `False`                                   | 是否使用绝对论文目录路径。                                                                                                         |
| `agent.index.recurse_subdirectories`            | `True`                                    | 索引时是否递归到子目录。                                                                                                           |
| `agent.index.concurrency`                        | `5`                                       | 并发文件系统读取数。                                                                                                               |
| `agent.index.sync_with_paper_directory`          | `True`                                    | 加载时是否同步索引与论文目录。                                                                                                      |
| `agent.index.batch_size`                         | `1`                                       | 提交索引之前要处理的文件数。                                                                                                       |
| `agent.index.files_filter`                      | `lambda f: f.suffix in {...}`            | 标记论文目录中要索引的文件的过滤函数。                                                                                              |

## 如何获取论文？

这确实是个好问题！
最好直接下载您认为有助于回答您问题的论文 PDF，然后从那里开始。

请参阅[关于 zotero、openreview 和解析的详细文档](docs/tutorials/where_do_I_get_papers.md)

## 回调函数

要在 LLM 补全的每个块上执行函数，
您需要提供一个可以在每个块上执行的函数。
例如，要获取补全的打字机视图，您可以这样做：

```python
from paperqa import Docs


def typewriter(chunk: str) -> None:
    print(chunk, end="")


docs = Docs()

# 添加一些文档...

await docs.aquery("什么是 PaperQA2？", callbacks=[typewriter])
```

### 缓存嵌入

通常，当您序列化 `Docs` 时，嵌入会被缓存，无论您使用什么向量存储。
因此，只要您保存底层 `Docs` 对象，
您应该能够避免重新嵌入文档。

## 自定义提示词

您可以使用设置自定义任何提示词。

```python
from paperqa import Docs, Settings

my_qa_prompt = (
    "回答问题 '{question}'\n"
    "如果有用的话使用下面的上下文。 "
    "您可以使用键来引用上下文，如 (pqac-abcd1234)。 "
    "如果没有足够的上下文，写一首关于您无法回答的诗。\n\n"
    "上下文: {context}"
)

docs = Docs()
settings = Settings()
settings.prompts.qa = my_qa_prompt
await docs.aquery("什么是 PaperQA2？", settings=settings)
```

### 前置和后置提示词

遵循上述语法，您还可以包含在查询之后和之前执行的提示词。
例如，您可以使用它来批评答案。

## 常见问题

### 为什么我的结果与论文中的不同？

在 FutureHouse 内部，我们有一套略有不同的工具。
我们正在尝试将其中一些（如引用遍历）放入这个仓库。
但是，我们有访问研究论文的 API 和许可证，我们无法公开分享。
同样，在我们的研究论文结果中，我们不是从已知的相关 PDF 开始的。
我们的代理必须使用关键词搜索从所有论文中识别它们，而不是仅仅从一个子集中识别。
我们正在逐步调整这两个版本的 PaperQA，
但直到有一种开源方式自由访问论文（即使是开源论文）
您将需要自己提供 PDF。

### 这与 LlamaIndex 或 LangChain 有什么不同？

[LangChain](https://github.com/langchain-ai/langchain)
和 [LlamaIndex](https://github.com/run-llama/llama_index)
都是用于处理 LLM 应用程序的框架，
为智能工作流和检索增强生成提供了抽象。

随着时间的推移，PaperQA 团队选择成为框架无关的，
而是将 LLM 驱动程序外包给 [LiteLLM][LiteLLM general docs]，
除了 Pydantic 及其工具外没有其他框架。
PaperQA 专注于科学论文及其元数据。

PaperQA 可以使用 LlamaIndex 或 LangChain 重新实现。
例如，我们的 `GatherEvidence` 工具可以重新实现为
带有基于 LLM 的重排序和上下文摘要的检索器。
LlamaIndex 中有类似的使用树响应方法的工作。

### 可以保存或加载吗？

`Docs` 类可以序列化和反序列化。
如果您想保存文档的嵌入然后稍后加载，这很有用。

```python
import pickle

# 保存
with open("my_docs.pkl", "wb") as f:
    pickle.dump(docs, f)

# 加载
with open("my_docs.pkl", "rb") as f:
    docs = pickle.load(f)
```

## 复现

[docs/2024-10-16_litqa2-splits.json5](docs/2024-10-16_litqa2-splits.json5)
中包含用于训练、评估和测试分割的问题 ID，
以及用于构建分割索引的论文 DOI。

- 训练和评估分割：问题 ID 来自
  [LAB-Bench 的 LitQA2 问题 ID](https://github.com/Future-House/LAB-Bench/blob/main/LitQA2/litqa-v2-public.jsonl)。
- 测试分割：问题 ID 来自
  [aviary-paper-data 的 LitQA2 问题 ID](https://huggingface.co/datasets/futurehouse/aviary-paper-data)。

有多篇论文逐渐构建了 PaperQA，如下所示在[引用](#引用)中。
要复现：

- `skarlinski2024language`：适用于训练和评估分割。
  测试分割保持不变。
- `narayanan2024aviarytraininglanguageagents`：训练、评估和测试分割都适用。

关于如何使用 LitQA 进行评估的示例，请参见
[aviary.litqa](https://github.com/Future-House/aviary/tree/main/packages/litqa#running-litqa)。

## 引用

如果您使用此软件，请阅读并引用以下论文：

```bibtex
@article{narayanan2024aviarytraininglanguageagents,
      title = {Aviary: training language agents on challenging scientific tasks},
      author = {
      Siddharth Narayanan and
 James D. Braza and
 Ryan-Rhys Griffiths and
 Manu Ponnapati and
 Albert Bou and
 Jon Laurent and
 Ori Kabeli and
 Geemi Wellawatte and
 Sam Cox and
 Samuel G. Rodriques and
 Andrew D. White},
      journal = {arXiv preprent arXiv:2412.21154},
      year = {2024},
      url = {https://doi.org/10.48550/arXiv.2412.21154},
}
```

```bibtex
@article{skarlinski2024language,
    title = {Language agents achieve superhuman synthesis of scientific knowledge},
    author = {
    Michael D. Skarlinski and
 Sam Cox and
 Jon M. Laurent and
 James D. Braza and
 Michaela Hinks and
 Michael J. Hammerling and
 Manvitha Ponnapati and
 Samuel G. Rodriques and
 Andrew D. White},
    journal = {arXiv preprent arXiv:2409.13740},
    year = {2024},
    url = {https://doi.org/10.48550/arXiv.2409.13740}
}
```

```bibtex
@article{lala2023paperqa,
    title = {PaperQA: Retrieval-Augmented Generative Agent for Scientific Research},
    author = {
    Jakub Lála and
 Odhran O'Donoghue and
 Aleksandar Shtedritski and
 Sam Cox and
 Samuel G. Rodriques and
 Andrew D. White},
    journal = {arXiv preprint arXiv:2312.07559},
    year = {2023},
    url = {https://doi.org/10.48550/arXiv.2312.07559}
}
```
