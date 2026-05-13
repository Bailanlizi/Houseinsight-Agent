from __future__ import annotations

import argparse
import uuid

import pandas as pd

from server.agent.graph import run_agent
from server.agent.state import AgentState
from server.core.config import get_settings
from server.core.session_store import get_session_store
from langchain_core.messages import HumanMessage


def cmd_run(args: argparse.Namespace) -> int:
    df = pd.read_csv(args.csv)
    sid = str(uuid.uuid4())
    get_session_store().put(sid, df)
    s = get_settings()
    initial: AgentState = {
        "messages": [HumanMessage(content=args.goal)],
        "session_id": sid,
        "goal": args.goal,
        "max_iterations": args.max_iterations or s.max_iterations,
        "data_profile": {},
        "plan": [],
        "execution_history": [],
        "iteration": 0,
        "stop_reason": "",
        "should_finish": False,
        "final_answer": "",
    }
    out = run_agent(initial)
    print(out.get("final_answer", ""))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="houseinsight")
    sub = parser.add_subparsers(dest="command", required=True)
    p_run = sub.add_parser("run", help="运行一次分析（本地 CSV）")
    p_run.add_argument("--csv", required=True)
    p_run.add_argument("--goal", default="分析这个数据集")
    p_run.add_argument("--max-iterations", type=int, default=None)
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
