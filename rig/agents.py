#!/usr/bin/env python3
"""Which coding agent plays, and how to read what it did.

The harness does not care who is at the controls: something reads `CLAUDE.md`,
runs `./act`, and writes files. But the two CLIs that can do that disagree on
everything else — how to be run headlessly, what their event streams look like,
and whether they will tell you what a session cost. This is the whole of that
difference, so the rest of the harness can stay ignorant of it.

Both must be able to answer three questions about a stream: how many turns and
tool calls happened, what the session cost, and — for the audit — every command
the agent ran and every file it wrote.
"""

import os
from pathlib import Path
from typing import Any, Protocol

# Claude Code reports its own spend; Codex reports tokens and leaves the
# arithmetic to the caller, so a price is needed to compare the two.
#
# Dollars per million tokens, and the one thing here that is not measured.
# OpenAI's own pricing page renders client-side and could not be read, so these
# come from two independent trackers that agree: openrouter.ai and
# aipricing.guru, July 2026. Cache writes cost more than fresh input and are
# most of the bill on a short session, so they are priced separately rather
# than folded in.
#
# Not modelled: requests over 272K input tokens bill at 2x input and 1.5x
# output for the whole request. These usage figures are per session, not per
# request, so that cannot be applied honestly — which makes the cost of a long
# game a floor rather than a figure.
PRICES: dict[str, dict[str, float]] = {
    "gpt-5.6-sol": {"input": 5.00, "cached": 0.50, "write": 6.25, "output": 30.00},
}


class Agent(Protocol):
    name: str
    model: str

    def argv(self, task: str, model: str, ws: Path) -> list[str]: ...
    def absorb(self, report: Any, event: dict) -> None: ...
    def ran(self, event: dict) -> list[str]: ...
    def results(self, event: dict) -> list[str]: ...
    def web(self, event: dict) -> int: ...


class Claude:
    """`claude -p`, streaming its own structured events."""

    name = "claude"
    model = "claude-opus-5"
    # The agent acts through ./act and reasons with a shell and files, so these
    # are pre-approved for an unattended session.
    #
    # This is approval, not availability: the session still registers WebSearch,
    # WebFetch and the rest, and a call to one would be recorded and then denied
    # for want of anyone to approve it. Do not read this list as a claim that the
    # web is out of reach — the counter below is what establishes that.
    ALLOWED = "Bash,Read,Write,Edit,Grep,Glob"
    # Empty means the CLI's own default, which for Opus 5 is `high` — that is
    # what every pass so far ran at, and leaving it unset keeps them reproducible.
    # `max` is session-only, which is exactly right when it is passed per session.
    LEVELS = ("low", "medium", "high", "xhigh", "max")
    EFFORT = os.environ.get("ARCSEC_EFFORT", "")

    def argv(self, task: str, model: str, ws: Path) -> list[str]:
        argv = [
            "claude",
            "-p",
            task,
            "--model",
            model,
            "--output-format",
            "stream-json",
            "--verbose",
            "--allowedTools",
            self.ALLOWED,
        ]
        if self.EFFORT:
            if self.EFFORT not in self.LEVELS:
                raise SystemExit(f"claude: effort {self.EFFORT!r} is not one of {self.LEVELS}")
            argv += ["--effort", self.EFFORT]
        return argv

    def absorb(self, report: Any, event: dict) -> None:
        kind = event.get("type")
        if kind == "assistant":
            report.turns += 1
            said = event.get("message", {}).get("content", [])
            report.tool_calls += sum(1 for b in said if b.get("type") == "tool_use")
        elif kind == "system" and event.get("subtype") == "compact_boundary":
            report.compactions += 1
        elif kind == "result":
            usage = event.get("usage", {})
            report.cost_usd = event.get("total_cost_usd", 0.0)
            report.input_tokens = usage.get("input_tokens", 0)
            report.output_tokens = usage.get("output_tokens", 0)
            report.cache_read_tokens = usage.get("cache_read_input_tokens", 0)
            report.cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)

    def ran(self, event: dict) -> list[str]:
        if event.get("type") != "assistant":
            return []
        said = []
        for block in event.get("message", {}).get("content", []):
            kind = block.get("type")
            # A server tool — web_search, web_fetch — runs on the provider's
            # infrastructure rather than in the sandbox, so no network rule can
            # see it. It arrives as its own block type, which this used to skip.
            if kind == "server_tool_use":
                said.append(f"{block.get('name', '')} {block.get('input', {})}")
                continue
            if kind != "tool_use":
                continue
            got = block.get("input", {})
            said.append(str(got.get("command", "")))
            said.append(str(got.get("content", "")) + str(got.get("new_string", "")))
        return said

    def web(self, event: dict) -> int:
        """How many web requests the provider says this session made.

        Reported by the API in the result event's usage, not by the agent and not
        by the CLI, so nothing inside the sandbox can shade it. It is the only
        check here that covers a tool executing on the provider's own machines,
        where the fence has no view at all.
        """
        if event.get("type") != "result":
            return 0
        counts = (event.get("usage") or {}).get("server_tool_use") or {}
        return sum(int(v) for k, v in counts.items() if k.endswith("_requests"))

    def results(self, event: dict) -> list[str]:
        if event.get("type") != "user":
            return []
        out = []
        for block in event.get("message", {}).get("content", []):
            if block.get("type") != "tool_result":
                continue
            body = block.get("content", "")
            if isinstance(body, list):
                body = " ".join(str(p.get("text", "")) for p in body if isinstance(p, dict))
            out.append(str(body))
        return out


class Codex:
    """`codex exec --json`.

    Sandboxed to the workspace with network access, because the agent has to
    reach the broker; approvals off, because nobody is watching. Codex's own
    sandbox is redundant inside the E2B fence but costs nothing and is the honest way to
    ask, rather than the flag named for bypassing it.
    """

    name = "codex"
    model = "gpt-5.6-sol"
    # How hard it thinks per turn. Set once for a whole batch through the
    # environment, because it belongs to the run rather than to a game, and the
    # upper levels cost enough to be a deliberate choice rather than a default.
    # `max` and `ultra` sit above `xhigh` for this model, so the published Codex
    # pass was not run at its ceiling. This used to rewrite a requested `max`
    # down to `xhigh`, which silently capped a batch that asked to think harder.
    LEVELS = ("minimal", "low", "medium", "high", "xhigh", "max", "ultra")
    EFFORT = os.environ.get("ARCSEC_EFFORT", "high")

    def argv(self, task: str, model: str, ws: Path) -> list[str]:
        return [
            "codex",
            "exec",
            "--json",
            "-m",
            model,
            "-c",
            f"model_reasoning_effort={self.EFFORT}",
            "-c",
            "approval_policy=never",
            "-c",
            "sandbox_workspace_write.network_access=true",
            "-s",
            "workspace-write",
            "--skip-git-repo-check",
            "-C",
            str(ws),
            task,
        ]

    def absorb(self, report: Any, event: dict) -> None:
        kind = event.get("type")
        item = event.get("item", {})
        if kind == "item.completed" and item.get("type") == "agent_message":
            # Codex counts one turn per prompt, so a whole session is one turn.
            # Its messages are the closer analogue of Claude's assistant turns.
            report.turns += 1
        elif kind == "item.completed" and item.get("type") == "command_execution":
            report.tool_calls += 1
        elif kind == "turn.completed":
            usage = event.get("usage", {})
            report.input_tokens = usage.get("input_tokens", 0)
            # Reasoning tokens are billed as output and are most of the spend on
            # a hard game, so they belong in the output count, not beside it.
            report.output_tokens = usage.get("output_tokens", 0) + usage.get(
                "reasoning_output_tokens", 0
            )
            report.cache_read_tokens = usage.get("cached_input_tokens", 0)
            report.cache_creation_tokens = usage.get("cache_write_input_tokens", 0)
            report.cost_usd = cost(report)

    def ran(self, event: dict) -> list[str]:
        item = event.get("item", {})
        if event.get("type") != "item.completed":
            return []
        if item.get("type") == "command_execution":
            return [str(item.get("command", ""))]
        if item.get("type") in ("file_change", "patch_apply"):
            return [str(item)]
        return []

    def results(self, event: dict) -> list[str]:
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "command_execution":
            return [str(item.get("aggregated_output", ""))]
        return []

    def web(self, event: dict) -> int:
        """Codex reports no such counter, so this says nothing rather than zero.

        For Codex the commands are the evidence, and they were enough: the four
        sessions that went looking for solutions were caught by the patterns in
        audit.py, from the commands they ran.
        """
        return 0


def cost(report: Any) -> float:
    """What a Codex session cost, if the price of its model is known.

    Zero means it is not, which is the honest answer — an invented price would
    quietly become the number in a comparison table.

    `input_tokens` is the total and the cached and written counts are parts of
    it, so fresh input is what is left over. Priced apart because they differ by
    more than tenfold, and most of a session's input is cache traffic.
    """
    price = PRICES.get(getattr(report, "model", ""))
    if not price:
        return 0.0
    cached, written = report.cache_read_tokens, report.cache_creation_tokens
    fresh = max(0, report.input_tokens - cached - written)
    return (
        fresh * price["input"]
        + cached * price["cached"]
        + written * price["write"]
        + report.output_tokens * price["output"]
    ) / 1_000_000


AGENTS: dict[str, Agent] = {"claude": Claude(), "codex": Codex()}
