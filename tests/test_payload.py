"""The sandbox gets a list of files, not the repository.

Twice a module was added to the harness and not to that list, and both times
every sandbox in the batch died on the import before taking a single action —
`agents.py` for a codex run, `audit.py` for a fenced one. The launcher cannot
catch it, because on this machine the import always works.

Moving the support code into `rig/` made that worse rather than better: the
payload now carries a shape as well as a set of names, and a file written to
the wrong depth is a module that resolves to nothing. So this reconstructs the
shipped tree in a temporary directory and imports it there, which is as close
to the sandbox as a test with no network can get.

Parsed rather than imported: cloud.py needs the e2b SDK, which is not a project
dependency, and this has to run in an ordinary test session.
"""

import ast
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def payload() -> list[str]:
    tree = ast.parse((REPO / "rig" / "cloud.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == "PAYLOAD" for t in node.targets
        ):
            return [ast.literal_eval(e) for e in node.value.elts]
    raise AssertionError("cloud.py has no PAYLOAD")


def imports(source: Path) -> set[str]:
    """Sibling modules this file imports — the ones that must travel with it."""
    found = set()
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node, ast.Import):
            found |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return {n for n in found if (REPO / f"{n}.py").exists() or (REPO / "rig" / f"{n}.py").exists()}


def test_the_payload_names_files_that_exist():
    for name in payload():
        assert (REPO / name).exists(), f"PAYLOAD lists {name}, which is not in the repository"


def test_every_module_the_payload_needs_travels_with_it():
    shipped = payload()
    stems = {Path(name).stem for name in shipped if name.endswith(".py")}
    for name in shipped:
        if not name.endswith(".py"):
            continue
        for needed in imports(REPO / name):
            assert needed in stems, (
                f"{name} imports {needed}, which is not in cloud.py's PAYLOAD — "
                "every sandbox in the batch would die on the import"
            )


def test_the_shipped_tree_can_import_itself(tmp_path):
    """The check the flat layout never needed.

    A payload entry carries a path now, so a file can be present and still be
    unimportable by being at the wrong depth. This copies exactly what a sandbox
    is sent — nothing else from the repository — and imports the two modules a
    session actually starts from.
    """
    for name in payload():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / name, target)

    done = subprocess.run(
        [sys.executable, "-c", "import run, act, db, agents, audit, broker"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, (
        "the shipped tree cannot import itself — a sandbox would die here:\n"
        + done.stderr[-1500:]
    )


def test_the_image_bakes_the_environment_and_not_the_code():
    """The template copies only what `uv sync` needs.

    Baking the sources too would leave a flattened `rig/db.py` at the work root,
    where `import db` finds it before the fresh copy the launcher writes — a
    stale module that looks exactly like a working one.
    """
    source = (REPO / "rig" / "cloud.py").read_text()
    assert '.copy(["pyproject.toml", "uv.lock"]' in source
    assert ".copy(PAYLOAD" not in source
    # and the copy has to resolve from the repo root, not from rig/
    assert "Template(file_context_path=REPO)" in source
