"""仕組みを守るテストの設定。

hook や設定の置き場所を変えたら、ここ（先頭の設定値）だけを直す。
"""

from pathlib import Path

import pytest

# ---- 設定値 ---------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
# hook を登録している Claude Code の設定
SETTINGS_PATH = REPO_ROOT / ".claude" / "settings.json"
# hook の本体と、設定の command に含まれているはずの文字列
GUARD_PATH = REPO_ROOT / ".claude" / "hooks" / "guard.sh"
GUARD_COMMAND_PART = ".claude/hooks/guard.sh"
# hook が見張る道具
GUARDED_TOOLS = {"Bash", "Edit", "Write"}
# テストの書き換えを検知するスクリプト
TAMPER_CHECK_PATH = REPO_ROOT / ".github" / "scripts" / "check_test_tamper.py"
# --------------------------------------------------------------------------


@pytest.fixture
def settings_path() -> Path:
    return SETTINGS_PATH


@pytest.fixture
def guard_path() -> Path:
    return GUARD_PATH


@pytest.fixture
def guard_command_part() -> str:
    return GUARD_COMMAND_PART


@pytest.fixture
def guarded_tools() -> set[str]:
    return GUARDED_TOOLS


@pytest.fixture
def tamper_check_path() -> Path:
    return TAMPER_CHECK_PATH
