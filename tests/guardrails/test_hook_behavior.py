"""hook（guard.sh）が止めるべき操作を止め、普通の操作は通すか。

Claude Code と同じ形の JSON を標準入力で渡し、終了コードで確かめる。
止める：終了コード 2（理由は標準エラー）／通す：終了コード 0。
"""

import json
import re
import subprocess

import pytest

# Edit・Write の file_path は、Claude Code では絶対パスで来る
ROOT = "/work/repo"

DENY = [
    pytest.param("Bash", {"command": "rm -rf build"}, id="recursive-rm"),
    pytest.param("Bash", {"command": "git push origin main"}, id="push-to-main"),
    pytest.param("Edit", {"file_path": f"{ROOT}/.claude/hooks/guard.sh"}, id="edit-hooks"),
    pytest.param(
        "Bash", {"command": "echo 'exit 0' > .claude/hooks/guard.sh"}, id="redirect-to-hooks"
    ),
    pytest.param("Write", {"file_path": f"{ROOT}/.claude/settings.json"}, id="write-settings"),
    pytest.param("Edit", {"file_path": f"{ROOT}/.claude/settings.json"}, id="edit-settings"),
    pytest.param(
        "Bash", {"command": "sed -i 's/guard/x/' .claude/settings.json"}, id="sed-settings"
    ),
]

ALLOW = [
    pytest.param("Bash", {"command": "git push origin feature/x"}, id="push-to-work-branch"),
    pytest.param("Edit", {"file_path": f"{ROOT}/src/booking.py"}, id="edit-src"),
    pytest.param("Bash", {"command": "rm build/a.txt"}, id="rm-one-file"),
    pytest.param(
        "Edit", {"file_path": f"{ROOT}/.claude/settings.local.json"}, id="edit-settings-local"
    ),
    pytest.param("Bash", {"command": "cat .claude/settings.json"}, id="read-settings"),
    pytest.param("Bash", {"command": "pytest -q"}, id="run-pytest"),
]


def run_guard(guard_path, tool_name, tool_input, cwd):
    payload = {
        "hook_event_name": "PreToolUse",
        "cwd": str(cwd),
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    return subprocess.run(
        ["bash", str(guard_path)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


@pytest.mark.parametrize(("tool_name", "tool_input"), DENY)
def test_guard_denies(guard_path, tmp_path, tool_name, tool_input):
    result = run_guard(guard_path, tool_name, tool_input, tmp_path)
    assert result.returncode == 2, f"止めるべき操作が通りました：{tool_name} {tool_input}"
    assert "止めた理由" in result.stderr
    assert "代わりに" in result.stderr


@pytest.mark.parametrize(("tool_name", "tool_input"), ALLOW)
def test_guard_allows(guard_path, tmp_path, tool_name, tool_input):
    result = run_guard(guard_path, tool_name, tool_input, tmp_path)
    assert result.returncode == 0, (
        f"通すべき操作が止まりました：{tool_name} {tool_input}\n{result.stderr}"
    )


def test_guard_has_no_variable_followed_by_wide_char(guard_path):
    """変数のすぐ後ろに全角の文字が無いこと（"$x（" ではなく "${x}（" と書く）。

    macOS の bash 3.2 は日本語のロケールで "$x（" を変数 x（ と読み違えて落ちる。
    Linux の bash 5 では起きないので、CI では書き方そのものを確かめる。
    """
    found = []
    for no, line in enumerate(guard_path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        found += [
            f"{no}: {m.group(0)}"
            for m in re.finditer(r"\$[A-Za-z_][A-Za-z0-9_]*(?=[^\x00-\x7f])", line)
        ]
    assert not found, "変数を ${...} で囲んでください：" + ", ".join(found)
