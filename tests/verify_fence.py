#!/usr/bin/env python3
"""Prove the egress fence, against the real thing.

    uv run --with e2b --with python-dotenv tests/verify_fence.py

A fence is not a unit-testable property: what matters is whether a live sandbox
actually refuses a live host, and E2B's own docs warn that a blocked TCP connect
can look like a success from inside. So this asks for real payloads and reports
what came back. It builds its allow list with `cloud.fence`, so it verifies the
harness's code rather than a copy of it.

Everything must hold at once: the hosts a game needs answer, every other host is
refused, and both CLIs still run. It exits non-zero naming whatever failed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cloud  # noqa: E402

CURL = "curl -sS -m 25 -o /dev/null -w '%{http_code}'"
# Hosts that would turn a score into nothing. `raw.githubusercontent.com` has
# served these games' own source files; a search engine serves everything written
# about them; `1.1.1.1` is the fence tested without a name to match on.
FORBIDDEN = {
    "example.com": f"{CURL} https://example.com/",
    "example.com over ipv6": f"{CURL} -6 https://example.com/",
    "github raw": f"{CURL} https://raw.githubusercontent.com/README.md",
    "github": f"{CURL} https://github.com/",
    "search": f"{CURL} 'https://www.google.com/search?q=arc+agi+3+ls20'",
    "pypi": f"{CURL} https://pypi.org/simple/",
    "the game api": f"{CURL} -X POST {cloud.act.BASE_URL}/api/scorecard/open",
    "a sibling subdomain": f"{CURL} https://console.anthropic.com/",
    "a bare address": f"{CURL} -k https://1.1.1.1/",
}
WORKS = {
    "claude": "timeout 180 claude -p 'reply with the single word ok' --model claude-opus-5",
    "codex": "printenv OPENAI_API_KEY | codex login --with-api-key >/dev/null && "
    "timeout 240 codex exec -m gpt-5.6-sol -c model_reasoning_effort=low"
    " -c approval_policy=never -s workspace-write --skip-git-repo-check"
    " 'reply with the single word ok' 2>&1 | tail -1",
    # The venv is baked into the template, so a fenced sandbox must not need an
    # index to start. If this fails, pyproject changed and the template is stale.
    "the harness": f"cd {cloud.WORK} && uv run python -c 'import arcengine; print(\"ok\")'",
}


def say(label: str, verdict: bool, detail: str) -> bool:
    print(f"  {'pass' if verdict else 'FAIL'}  {label:24} {detail}")
    return verdict


def main() -> int:
    # Both agents are exercised, so both credentials must be there.
    cloud.secrets("claude")
    keys = cloud.secrets("codex")
    neon = cloud.host_of(keys["POSTGRES_DSN"])
    sandbox = cloud.Sandbox.create(
        template=cloud.TEMPLATE,
        timeout=900,
        metadata={"run": "verify-fence"},
        envs={
            "ANTHROPIC_API_KEY": keys["ANT_API_KEY"],
            "OPENAI_API_KEY": keys["OPENAI_API_KEY"],
        },
        network=cloud.fence(cloud.MODEL_HOST["claude"], cloud.MODEL_HOST["codex"], neon),
    )
    print(f"sandbox {sandbox.sandbox_id}\n")

    def run(command: str, seconds: int = 90) -> str:
        """A refusal is a result, so a non-zero exit must not raise."""
        got = sandbox.commands.run(
            f'{command} 2>&1; echo " exit=$?"', timeout=seconds, request_timeout=seconds + 30
        )
        return " ".join((got.stdout or "").split())[-200:]

    ok = True
    try:
        print("refused:")
        for label, command in FORBIDDEN.items():
            out = run(command)
            ok &= say(label, "exit=0" not in out, out)

        print("\nreachable:")
        for label, host in [("model api", cloud.MODEL_HOST["claude"]), ("the record", neon)]:
            out = run(f"{CURL} https://{host}/")
            ok &= say(label, "exit=0" in out, out)

        print("\nstill works:")
        for label, command in WORKS.items():
            out = run(command, seconds=400)
            ok &= say(label, "exit=0" in out, out)
    finally:
        sandbox.kill()

    print("\nthe fence holds" if ok else "\nthe fence LEAKS — see FAIL above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
