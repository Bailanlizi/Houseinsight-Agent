from __future__ import annotations

# 默认面向用户输出为简体中文（SPEC）
SYSTEM_ZH = (
    "你是 HouseInsight 二手房数据分析智能体。请使用简体中文进行面向用户的总结与说明。"
    "你只能建议调用已注册工具完成数据操作，不得执行任意代码。"
)

PLAN_PROMPT = """根据用户目标、数据摘要与执行历史，制定下一步要调用的工具（通常 1 步，最多 3 步）。
你必须输出 JSON，格式如下：
{{
  "steps": [
    {{"tool": "工具名", "arguments": {{...}}, "rationale": "可选，中文简述原因"}}
  ]
}}
可用工具名称：
{tool_names}

当前数据摘要（节选）：
{profile_excerpt}

用户目标：
{goal}

执行历史摘要：
{history_excerpt}
"""

OBSERVE_PROMPT = """根据最近一次工具执行结果与用户目标，判断是否应结束分析循环。
输出 JSON：
{{
  "should_finish": true/false,
  "stop_reason": "completed|error|max_iterations 之一（若 should_finish 为 false 可填 completed 占位）",
  "notes": "中文简短说明"
}}

用户目标：
{goal}

最近一次工具结果：
{last_result}
"""

ANSWER_PROMPT = """基于下列信息，用简体中文生成结构清晰、有洞察的最终回答（可含小标题与要点）。
若信息不足，诚实说明局限。

用户目标：
{goal}

数据摘要：
{profile_excerpt}

执行历史要点：
{history_excerpt}
"""
