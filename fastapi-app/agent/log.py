"""可观测日志：写入 agent_run_log（node/intent/输入输出/tool_calls/耗时/状态）。"""
from models import AgentRunLog


async def write_log(analysis_id, node, intent="", input_data=None, output_data=None,
                    tool_calls=None, duration_ms=None, status=1):
    await AgentRunLog.create(
        analysis_id=analysis_id,
        node=node,
        intent=intent,
        input=input_data,
        output=output_data,
        tool_calls=tool_calls,
        duration_ms=duration_ms,
        status=status,
    )
