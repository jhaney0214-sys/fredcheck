"""Put the FRED questions to Claude, with and without FRED's MCP connector.

Each question is asked once per arm, in a fresh conversation, with no system
prompt beyond the date (the way a person would ask). Full responses, tool
calls, model and token usage are saved to runs/<date>/<arm>.jsonl for grading.

    python run.py                      # both arms, all 50
    python run.py --arms fred --only L01,V03
    python run.py --arms bare,fred,web # add a web-search arm

Arms:
  bare  no tools: what the model knows
  fred  FRED's official MCP connector (needs: python fred_auth.py)
  web   Anthropic's web search tool: what a person with search would get

Needs ANTHROPIC_API_KEY in the environment.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import anthropic

HERE = Path(__file__).parent
MODEL = "claude-opus-5-5"
EFFORT = "medium"  # the model's default; stated so runs are comparable
FRED_URL = "https://mcp.stlouisfed.org/"
BETAS_FRED = ["mcp-client-2025-11-20"]
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def ask(client, q, arm, today):
    betas = [FALLBACK_BETA] + (BETAS_FRED if arm == "fred" else [])
    kwargs: dict = dict(
        model=MODEL,
        max_tokens=16000,
        system="Today's date is %s." % today,
        messages=[{"role": "user", "content": q["q"]}],
        output_config={"effort": EFFORT},
        # On a safety decline the API re-runs the request on a fallback model;
        # response.model then records which model actually answered.
        betas=betas,
        fallbacks="default",
    )
    if arm == "fred":
        from fred_auth import access_token
        kwargs["mcp_servers"] = [{"type": "url", "url": FRED_URL, "name": "fred",
                                  "authorization_token": access_token()}]
        kwargs["tools"] = [{"type": "mcp_toolset", "mcp_server_name": "fred"}]
    elif arm == "web":
        kwargs["tools"] = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}]

    with client.beta.messages.stream(**kwargs) as stream:
        msg = stream.get_final_message()

    text = "".join(b.text for b in msg.content if b.type == "text")
    tools = [{"type": b.type, "name": getattr(b, "name", None), "input": getattr(b, "input", None)}
             for b in msg.content if b.type in ("mcp_tool_use", "server_tool_use")]
    return {
        "id": q["id"], "arm": arm, "question": q["q"], "answer": text,
        "tool_calls": tools, "model": msg.model, "stop_reason": msg.stop_reason,
        "usage": msg.usage.to_dict(), "request_id": msg._request_id,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="bare,fred")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    qs = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))["questions"]
    if args.only:
        keep = set(args.only.split(","))
        qs = [q for q in qs if q["id"] in keep]
    today = dt.date.today().isoformat()
    out_dir = HERE / "runs" / today
    out_dir.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()

    for arm in args.arms.split(","):
        path = out_dir / ("%s.jsonl" % arm)
        done = set()
        if path.exists():  # resume: skip questions already answered today
            done = {json.loads(l)["id"] for l in path.read_text(encoding="utf-8").splitlines() if l}
        with path.open("a", encoding="utf-8") as f:
            for q in qs:
                if q["id"] in done:
                    continue
                try:
                    row = ask(client, q, arm, today)
                except anthropic.APIStatusError as e:
                    print("%s %s: API error %s %s" % (arm, q["id"], e.status_code, e.message), file=sys.stderr)
                    continue
                f.write(json.dumps(row) + "\n")
                f.flush()
                u = row["usage"]
                print("%-4s %s  in %6s out %5s  tools %d  %s" % (
                    arm, q["id"], u.get("input_tokens"), u.get("output_tokens"),
                    len(row["tool_calls"]), row["answer"][:70].replace("\n", " ")))


if __name__ == "__main__":
    main()
