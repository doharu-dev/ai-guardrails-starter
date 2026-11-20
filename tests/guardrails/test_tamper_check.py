"""テストの書き換えを検知するスクリプト（.github/scripts/check_test_tamper.py）の判定。

一時的な git のリポジトリを作り、base と head の差分と PR 本文を渡して、終了コードで確かめる。
緑：終了コード 0／赤：終了コード 1。
"""

import os
import subprocess
import sys

import pytest

NO_REASON = "## 変更の内容\n境界の扱いを変えました。\n"
REASON = (
    NO_REASON + "\n## テストを変えた理由\n運用を変え、終了と開始が同じ時刻でも重なると扱うため。\n"
)

ORIGINAL = "def test_a():\n    assert 1 == 1\n\n\ndef test_b():\n    assert 2 == 2\n"


def git(repo, *args):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=", *args],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """tests/test_x.py と src/app.py が入った base のコミットを持つリポジトリ。"""
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "tests").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text(ORIGINAL)
    (tmp_path / "src" / "app.py").write_text("x = 1\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def commit(repo, files):
    for name, text in files.items():
        (repo / name).write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "change")


def judge(repo, script, body):
    env = {
        **os.environ,
        "TEST_PATHS": "tests/",
        "BASE_SHA": git(repo, "rev-parse", "HEAD~1"),
        "HEAD_SHA": git(repo, "rev-parse", "HEAD"),
        "PR_BODY": body,
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


SKIP_LINE = "\n\n@pytest.mark.skip(reason='later')\ndef test_c():\n    assert 3 == 3\n"

CASES = [
    # (id, 変えるファイル, PR 本文, 期待する終了コード)
    ("no-test-change", {"src/app.py": "x = 2\n"}, NO_REASON, 0),
    (
        "test-added-only",
        {"tests/test_x.py": ORIGINAL + "\n\ndef test_c():\n    pass\n"},
        NO_REASON,
        0,
    ),
    (
        "changed-no-reason",
        {"tests/test_x.py": ORIGINAL.replace("2 == 2", "2 == 3")},
        NO_REASON,
        1,
    ),
    ("changed-with-reason", {"tests/test_x.py": ORIGINAL.replace("2 == 2", "2 == 3")}, REASON, 0),
    ("skip-added-no-reason", {"tests/test_x.py": ORIGINAL + SKIP_LINE}, NO_REASON, 1),
    ("skip-added-with-reason", {"tests/test_x.py": ORIGINAL + SKIP_LINE}, REASON, 0),
]


@pytest.mark.parametrize(
    ("files", "body", "expected"), [c[1:] for c in CASES], ids=[c[0] for c in CASES]
)
def test_judge(repo, tamper_check_path, files, body, expected):
    commit(repo, files)
    result = judge(repo, tamper_check_path, body)
    assert result.returncode == expected, result.stdout + result.stderr


@pytest.mark.parametrize(
    "line",
    [
        "@pytest.mark.skipif(True, reason='x')",
        "@pytest.mark.xfail",
        "    pytest.skip('x')",
        "@unittest.skip('x')",
    ],
)
def test_other_skip_patterns_are_red(repo, tamper_check_path, line):
    commit(repo, {"tests/test_x.py": ORIGINAL + f"\n\n{line}\ndef test_c():\n    pass\n"})
    assert judge(repo, tamper_check_path, NO_REASON).returncode == 1


def test_red_log_shows_file_and_line(repo, tamper_check_path):
    commit(repo, {"tests/test_x.py": ORIGINAL + SKIP_LINE})
    result = judge(repo, tamper_check_path, NO_REASON)
    assert "テストを無効にする書き方が足されています" in result.stdout
    assert "tests/test_x.py:9" in result.stdout
    assert "## テストを変えた理由" in result.stdout


def test_reason_with_only_html_comment_is_red(repo, tamper_check_path):
    commit(repo, {"tests/test_x.py": ORIGINAL + SKIP_LINE})
    body = "## テストを変えた理由\n<!-- ここに理由を書く -->\n"
    assert judge(repo, tamper_check_path, body).returncode == 1
