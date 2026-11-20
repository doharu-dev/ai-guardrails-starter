"""hook が Claude Code の設定に登録されているか。

.claude/settings.json から hook の登録が外されると、hook ごと効かなくなる。
登録が崩れたら、ここで赤にする。
"""

import json
import re


def registered_tools(settings: dict, command_part: str) -> set[str]:
    """PreToolUse で、command_part を含む hook が見張っている道具の集まりを返す。"""
    tools: set[str] = set()
    for entry in settings.get("hooks", {}).get("PreToolUse", []):
        commands = [
            hook.get("command", "")
            for hook in entry.get("hooks", [])
            if hook.get("type") == "command"
        ]
        if not any(command_part in command for command in commands):
            continue
        matcher = entry.get("matcher", "").strip()
        if matcher in ("", "*"):
            return {"*"}  # すべての道具が対象
        tools |= {name.strip() for name in re.split(r"[|,]", matcher)}
    return tools


def test_guard_script_exists(guard_path):
    assert guard_path.is_file(), f"hook の本体がありません：{guard_path}"


def test_guard_is_registered_for_bash_edit_write(settings_path, guard_command_part, guarded_tools):
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    tools = registered_tools(settings, guard_command_part)
    assert "*" in tools or guarded_tools <= tools, (
        f"{settings_path.name} の PreToolUse で、{guard_command_part} が "
        f"{sorted(guarded_tools)} を見張っていません（見張っている道具：{sorted(tools)}）"
    )
