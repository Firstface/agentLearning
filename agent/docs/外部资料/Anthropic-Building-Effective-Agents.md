# 构建高效的智能体（Building effective agents）

> 原文：<https://www.anthropic.com/engineering/building-effective-agents>
> 作者：Erik S.、Barry Zhang
> 发布于 2024 年 12 月 19 日

我们与数十个跨行业团队一起构建过 LLM 智能体。一个一以贯之的发现是：最成功的实现都采用了**简单、可组合的模式**，而不是复杂的框架。

在过去一年里，我们与数十个团队一起构建跨行业的大语言模型（LLM）智能体。一以贯之地，那些最成功的实现并没有使用复杂的框架或专门的库。相反，它们都是基于**简单、可组合的模式**搭建起来的。

在本文中，我们分享了我们从客户合作以及自己构建智能体的过程中所学到的经验，并为开发者提供构建高效智能体的实用建议。

## 什么是智能体（agent）？

"Agent"一词可以有多种定义。一些客户把它定义为**完全自主的系统**：它们在很长一段时间内独立运行，通过使用各种工具完成复杂任务。另一些人则用这个词来描述**遵循预定义工作流的、更具规约性的实现**。在 Anthropic，我们把上述所有变体统称为 **agentic systems（智能体系统）**，但在架构层面区分两个重要概念—— **workflows（工作流）** 与 **agents（智能体）**：

- **Workflows（工作流）** 是指 LLM 与工具通过**预先定义的代码路径**被编排起来的系统。
- **Agents（智能体）** 则是指 LLM **动态地**指挥自身流程与工具使用、自主控制如何完成任务的系统。

下面，我们将详细介绍这两种类型的 agentic systems。在附录 1（"Agents in Practice"）中，我们还描述了客户在使用这类系统时取得显著收益的两个领域。

## 什么时候用（以及不用）智能体

在使用 LLM 构建应用时，我们建议**优先寻求最简单的解决方案**，只有在必要时才增加复杂度。这甚至可能意味着压根不构建 agentic 系统。Agentic 系统通常以**延迟和成本**为代价换取更好的任务表现，你需要思考这种取舍是否合理。

当确实需要更高复杂度时：**workflows** 在已定义良好的任务上提供可预测性与一致性；而 **agents** 则在需要灵活性与模型驱动决策、且要规模化时更合适。然而，对许多应用而言，**用检索（retrieval）和 in-context examples 来优化单次 LLM 调用通常就已足够**。

## 什么时候、以及如何使用框架

有许多框架让构建 agentic 系统变得更容易，包括：

- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)；
- [AWS 出品的 Strands Agents SDK](https://strandsagents.com/latest/)；
- [Rivet](https://rivet.ironcladapp.com/)：拖拽式 GUI LLM 工作流构建器；以及
- [Vellum](https://www.vellum.ai/)：另一个用于构建和测试复杂工作流的 GUI 工具。

这些框架通过简化标准的低层任务（如调用 LLM、定义和解析工具、串联调用）让你更容易上手。然而，它们往往会引入**额外的抽象层**，掩盖底层的 prompt 与响应内容，使调试变得更难。它们也容易诱导你在更简单的方案就够用时仍然增加复杂度。

我们建议开发者**直接使用 LLM API 起步**——许多模式只需要几行代码就能实现。如果你确实要使用框架，请确保你理解它的底层代码。**对底层运作的错误假设**是常见的客户错误来源。

参考我们的 [cookbook](https://platform.claude.com/cookbook/patterns-agents-basic-workflows) 获取一些示例实现。

## 构建模块、工作流与智能体

在本节中，我们将介绍我们在生产中看到的常见 agentic 系统模式。我们将从基础构建模块——**augmented LLM**——开始，然后逐步增加复杂度，从简单的组合式工作流一直延展到自主智能体。

### 构建模块：增强型 LLM（Augmented LLM）

agentic 系统的基本构建模块是一个**被增强过的 LLM**——它配备了诸如检索、工具与记忆等增强能力。我们当前的模型可以**主动**使用这些能力——自行生成搜索 query、选择合适的工具，并决定要保留哪些信息。

*增强型 LLM 示意图*

我们建议在实现时聚焦两个关键方面：**针对你的具体用例裁剪这些能力**，以及**为 LLM 提供易用、文档良好的接口**。实现这些增强有许多方法，其中一种是通过我们最近发布的 [Model Context Protocol](https://www.anthropic.com/news/model-context-protocol)，它允许开发者通过简单的 [客户端实现](https://modelcontextprotocol.io/tutorials/building-a-client#building-mcp-clients) 接入一个不断壮大的第三方工具生态。

在本文余下部分，我们都假设每次 LLM 调用都已具备这些增强能力。

### 工作流：Prompt 链式调用（Prompt chaining）

Prompt chaining 把任务**拆解为一系列步骤**，每一次 LLM 调用都处理上一次调用的输出。你可以在任意中间步骤上加入**程序化检查**（见下图中的 "gate"）以确保流程仍在正轨上。

*Prompt chaining 工作流示意图*

**何时使用此工作流：** 当任务能够被清晰、干净地拆解为固定子任务时，这种工作流最理想。其主要目标是用**延迟换更高的准确度**——让每次 LLM 调用都成为一项更简单的任务。

**Prompt chaining 适用的示例：**

- 先生成一段营销文案，然后再把它翻译成另一种语言。
- 先写一份文档大纲，检查大纲是否满足某些标准，然后基于大纲撰写正文。

### 工作流：路由（Routing）

路由会先**对输入进行分类**，再把它分发到一个专门的后续任务上。这种工作流支持**关注点分离**，从而构建更专精的 prompt。如果不使用路由，针对一类输入做的优化可能反而会损害其他输入的表现。

*Routing 工作流示意图*

**何时使用此工作流：** 当复杂任务存在**显著不同、最好分别处理的类别**，并且分类可以被准确完成（无论是用 LLM 还是更传统的分类模型/算法）时，路由会很合适。

**路由适用的示例：**

- 把不同类型的客服请求（一般问题、退款请求、技术支持）路由到不同的下游流程、prompt 与工具中。
- 把简单/常见问题路由到更小且性价比更高的模型（如 Claude Haiku 4.5），把困难/不常见问题路由到能力更强的模型（如 Claude Sonnet 4.5），以获得最佳性价比。

### 工作流：并行化（Parallelization）

LLM 有时可以**同时**处理一项任务，再以编程方式聚合它们的输出。这种"并行化"工作流主要表现为两种关键变体：

- **Sectioning（分节）：** 把任务拆分为可并行运行的、相互独立的子任务。
- **Voting（投票）：** 多次运行同一个任务以获得多样化的输出。

*Parallelization 工作流示意图*

**何时使用此工作流：** 当被拆分的子任务可以并行以提升速度，或当需要从多个视角/多次尝试来获得更高置信度的结果时，并行化非常有效。对于包含**多种考量维度**的复杂任务，让每个维度由一次单独的 LLM 调用处理，通常能获得更好的表现，因为每次调用的注意力都更集中。

**并行化适用的示例：**

- **Sectioning：**
    - 实现 guardrails：一个模型实例处理用户 query，另一个模型实例对其进行不当内容/请求的筛查。这通常比让同一次 LLM 调用同时处理 guardrails 与核心响应表现更好。
    - 自动化 evals：每次 LLM 调用评估模型在给定 prompt 上某一个维度的表现。
- **Voting：**
    - 用多种不同的 prompt 来审查同一段代码的漏洞，每个 prompt 各自给出标记。
    - 判断一段内容是否不当：用多个 prompt 评估不同维度，或要求不同的投票阈值，以平衡误报（false positive）与漏报（false negative）。

### 工作流：编排者-工人（Orchestrator-workers）

在 orchestrator-workers 工作流中，一个**中心 LLM 动态地**拆分任务、把子任务委派给"工人 LLM"，并把它们的结果综合起来。

*Orchestrator-workers 工作流示意图*

**何时使用此工作流：** 这种工作流非常适合**无法预知所需子任务**的复杂任务（例如在编码场景，需要修改的文件数量以及每个文件的修改性质，往往取决于具体任务）。它在拓扑结构上与并行化相似，但**关键区别在于灵活性**——子任务并非预先定义，而是由编排者根据具体输入动态决定。

**orchestrator-workers 适用的示例：**

- 每次都需要对多个文件进行复杂修改的编码产品。
- 需要从多个来源收集和分析信息以发现潜在相关内容的搜索类任务。

### 工作流：评估者-优化者（Evaluator-optimizer）

在 evaluator-optimizer 工作流中，一次 LLM 调用负责**生成响应**，另一次 LLM 调用则在循环中**给出评估与反馈**。

*Evaluator-optimizer 工作流示意图*

**何时使用此工作流：** 当我们有**清晰的评估标准**，并且**迭代式打磨能带来可衡量的价值**时，这种工作流尤其有效。判断它是否合适的两个信号：第一，当人类清晰表达反馈时，LLM 的回答确实可以被显著改进；第二，LLM 自身也能给出这种反馈。这类似于人类作者在写一份打磨过的文档时所经历的迭代写作过程。

**evaluator-optimizer 适用的示例：**

- 文学翻译：翻译者 LLM 一开始可能捕捉不到某些细微之处，而评估者 LLM 可以提供有用的批评。
- 复杂搜索：需要多轮搜索与分析才能收集到全面信息，由评估者决定是否还需要进一步搜索。

### 智能体（Agents）

随着 LLM 在关键能力上日益成熟——理解复杂输入、进行推理与规划、可靠地使用工具、以及从错误中恢复——**智能体正在生产环境中崭露头角**。智能体的工作通常以**人类用户的一条命令、或与其的交互式讨论**作为开端。一旦任务明确，智能体会**独立地规划与执行**，必要时再回到人类处获取更多信息或判断。在执行过程中，智能体在每一步都从环境中获取**"ground truth"**（如工具调用结果或代码执行结果）以评估自身进展，这一点至关重要。智能体可以在**检查点或遇到阻塞时**暂停以请求人类反馈。任务通常在完成时终止，但为保持可控性，往往也会包含**停止条件**（如最大迭代次数）。

智能体能处理复杂任务，但其实现往往很直接：它们通常就是**在循环中、根据环境反馈使用工具的 LLM**。因此，**周到、清晰地设计工具集及其文档至关重要**。我们在附录 2（"Prompt Engineering your Tools"）中进一步展开了关于工具开发的最佳实践。

*自主智能体示意图*

**何时使用智能体：** 智能体适合处理那些**开放性问题**——这些问题中，所需的步骤数难以甚至不可能预先预测，你也无法硬编码出固定路径。LLM 可能要运行许多轮，因此你必须对它的决策**有一定程度的信任**。智能体的自主性使其非常适合**在可信环境中扩大任务规模**。

智能体的自主性也意味着**更高的成本**以及**误差累积**的风险。我们建议在沙盒环境中进行充分测试，并配备恰当的 guardrails。

**智能体适用的示例：**

以下示例来自我们自己的实现：

- 一个用于解决 [SWE-bench 任务](https://www.anthropic.com/research/swe-bench-sonnet) 的编码智能体——它需要根据任务描述编辑许多文件；
- 我们的 [computer use 参考实现](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo)：Claude 通过操作计算机来完成任务。

*编码智能体的高层流程示意图*

## 组合并定制这些模式

这些构建模块**并不是规约性的**。它们是常见模式，开发者可以根据不同用例对其进行塑造与组合。任何 LLM 特性的成功关键，都是**度量性能并迭代实现**。再次强调：**只有当复杂度被证明能改善结果时，才应该考虑增加它**。

## 总结

在 LLM 领域，成功**不是关于构建最复杂的系统**，而是关于**为你的需求构建"对的"系统**。从简单的 prompt 起步，用全面的评估来优化它，**只有当更简单的方案不够用时，才引入多步 agentic 系统**。

在实现智能体时，我们尝试遵循三条核心原则：

1. 在智能体设计中保持 **简洁（simplicity）**。
2. 通过显式展示智能体的规划步骤，优先保证 **透明（transparency）**。
3. 通过周到的工具 **文档与测试**，精心打磨你的 **agent-computer interface (ACI)**。

框架可以帮你快速上手，但当你走向生产时，**不要犹豫去削减抽象层、用基础组件构建**。遵循这些原则，你能创造出不仅强大、而且可靠、可维护、并值得用户信任的智能体。

### 致谢

由 Erik S. 与 Barry Zhang 撰写。本文借鉴了我们在 Anthropic 构建智能体的经验，以及客户分享的宝贵洞见——我们对此深表感谢。

## 附录 1：智能体实践（Agents in practice）

我们与客户的合作中，发现两个特别有前景的 AI agent 应用，它们很好地展示了上文所讨论模式的实际价值。这两个应用都说明：**当任务同时需要对话与行动、有清晰的成功标准、能够形成反馈循环、并且整合了有意义的人类监督时**，agent 才能带来最大价值。

### A. 客户支持（Customer support）

客户支持把熟悉的聊天机器人界面与通过工具集成获得的增强能力结合起来。这是更开放式 agent 的天然适用场景，因为：

- 支持类对话天生遵循对话流，同时又需要访问外部信息和执行外部动作；
- 可以通过工具拉取客户数据、订单历史、知识库文章；
- 诸如发起退款、更新工单等动作可以通过程序化方式处理；并且
- 成功可以通过用户定义的"是否解决问题"被清晰地度量。

已有多家公司通过**按结果计费**（仅在成功解决问题时收费）的定价模式验证了这种方案的可行性，体现了他们对自家 agent 效果的信心。

### B. 编码 agent（Coding agents）

软件开发领域已展现出 LLM 特性的巨大潜力，能力从代码补全演进到自主问题求解。Agent 在这个领域尤其有效，因为：

- 代码方案可以通过自动化测试进行验证；
- Agent 可以使用测试结果作为反馈来迭代方案；
- 问题域定义良好、结构化清晰；并且
- 输出质量可以被客观度量。

在我们自己的实现中，agent 现在已经能够仅基于 PR 描述就解决 SWE-bench Verified 基准中的真实 GitHub issue。然而，尽管自动化测试可以验证功能正确性，**人工审查仍然是确保方案符合更广泛系统要求的关键**。

## 附录 2：为你的工具做 Prompt 工程（Prompt engineering your tools）

不管你在构建哪种 agent 系统，**工具很可能都是 agent 的重要组成部分**。工具让 Claude 能够通过我们 API 中精确指定的结构与定义，与外部服务和 API 交互。当 Claude 响应时，如果它打算调用工具，会在 API 响应中包含一个 tool use 块。**工具定义与规格应当与你整体的 prompt 一样，受到同等程度的 prompt engineering 关注**。本附录简要介绍如何为你的工具做 prompt engineering。

通常有多种方式可以表达同一个动作。例如，你可以通过写一段 diff 来指定文件编辑，也可以通过重写整个文件。对于结构化输出，你可以把代码放在 markdown 中返回，也可以放在 JSON 中返回。在软件工程角度看，这些差异只是表面的，可以无损地相互转换。然而，**有些格式对 LLM 来说要难写得多**。写 diff 需要在新代码写出之前就知道这块改了多少行（chunk header）；把代码写在 JSON 里（相对于 markdown）需要额外转义换行符和引号。

我们对选择工具格式的建议如下：

- **给模型留出足够多的 token 用来"思考"**，避免它把自己写进死角；
- **保持格式贴近模型在互联网文本中自然见过的样子**；
- **避免任何格式"开销"**，比如让模型精确地数几千行代码、或者对它写出来的代码做字符串转义。

一个经验法则是：想想你为人机交互界面（HCI）投入了多少精力，那就计划为 agent-computer interface（ACI）投入同等精力。下面是一些做好这件事的思路：

- **把自己代入模型的视角**。仅根据描述与参数，使用这个工具的方式是否一目了然？还是需要仔细思考？如果你都需要仔细想，那对模型大概也是这样。一个好的工具定义通常会包含**示例用法、边界情况、输入格式要求、以及与其他工具的清晰边界**。
- **如何修改参数名或描述让事情更明显**？把它当作给团队里的初级开发写一份优秀的 docstring。当你有许多相似工具时，这一点尤其重要。
- **测试模型如何使用你的工具**：在 workbench 中跑大量示例输入，观察模型会犯哪些错误，并据此迭代。
- **给你的工具做 Poka-yoke（防呆）设计**。修改参数让出错变得更困难。

在我们构建 SWE-bench agent 的过程中，**我们实际上花在优化工具上的时间，比花在整体 prompt 上的时间还要多**。例如，我们发现当 agent 离开根目录后，使用相对路径的工具会让模型出错。为了修复这个问题，我们把工具改成**始终要求绝对路径**——之后我们发现模型完美地使用了这一方法。

---

> 英文原文（Original English）

### Appendix 1: Agents in practice

Our work with customers has revealed two particularly promising applications for AI agents that demonstrate the practical value of the patterns discussed above. Both applications illustrate how agents add the most value for tasks that require both conversation and action, have clear success criteria, enable feedback loops, and integrate meaningful human oversight.

#### A. Customer support

Customer support combines familiar chatbot interfaces with enhanced capabilities through tool integration. This is a natural fit for more open-ended agents because:

- Support interactions naturally follow a conversation flow while requiring access to external information and actions;
- Tools can be integrated to pull customer data, order history, and knowledge base articles;
- Actions such as issuing refunds or updating tickets can be handled programmatically; and
- Success can be clearly measured through user-defined resolutions.

Several companies have demonstrated the viability of this approach through usage-based pricing models that charge only for successful resolutions, showing confidence in their agents' effectiveness.

#### B. Coding agents

The software development space has shown remarkable potential for LLM features, with capabilities evolving from code completion to autonomous problem-solving. Agents are particularly effective because:

- Code solutions are verifiable through automated tests;
- Agents can iterate on solutions using test results as feedback;
- The problem space is well-defined and structured; and
- Output quality can be measured objectively.

In our own implementation, agents can now solve real GitHub issues in the SWE-bench Verified benchmark based on the pull request description alone. However, whereas automated testing helps verify functionality, human review remains crucial for ensuring solutions align with broader system requirements.

### Appendix 2: Prompt engineering your tools

No matter which agentic system you're building, tools will likely be an important part of your agent. Tools enable Claude to interact with external services and APIs by specifying their exact structure and definition in our API. When Claude responds, it will include a tool use block in the API response if it plans to invoke a tool. Tool definitions and specifications should be given just as much prompt engineering attention as your overall prompts. In this brief appendix, we describe how to prompt engineer your tools.

There are often several ways to specify the same action. For instance, you can specify a file edit by writing a diff, or by rewriting the entire file. For structured output, you can return code inside markdown or inside JSON. In software engineering, differences like these are cosmetic and can be converted losslessly from one to the other. However, some formats are much more difficult for an LLM to write than others. Writing a diff requires knowing how many lines are changing in the chunk header before the new code is written. Writing code inside JSON (compared to markdown) requires extra escaping of newlines and quotes.

Our suggestions for deciding on tool formats are the following:

- Give the model enough tokens to "think" before it writes itself into a corner.
- Keep the format close to what the model has seen naturally occurring in text on the internet.
- Make sure there's no formatting "overhead" such as having to keep an accurate count of thousands of lines of code, or string-escaping any code it writes.

One rule of thumb is to think about how much effort goes into human-computer interfaces (HCI), and plan to invest just as much effort in creating good agent-computer interfaces (ACI). Here are some thoughts on how to do so:

- Put yourself in the model's shoes. Is it obvious how to use this tool, based on the description and parameters, or would you need to think carefully about it? If so, then it's probably also true for the model. A good tool definition often includes example usage, edge cases, input format requirements, and clear boundaries from other tools.
- How can you change parameter names or descriptions to make things more obvious? Think of this as writing a great docstring for a junior developer on your team. This is especially important when using many similar tools.
- Test how the model uses your tools: Run many example inputs in our workbench to see what mistakes the model makes, and iterate.
- Poka-yoke your tools. Change the arguments so that it is harder to make mistakes.

While building our agent for SWE-bench, we actually spent more time optimizing our tools than the overall prompt. For example, we found that the model would make mistakes with tools using relative filepaths after the agent had moved out of the root directory. To fix this, we changed the tool to always require absolute filepaths—and we found that the model used this method flawlessly.
