"""hook が Claude Code の設定に登録されているか。

.claude/settings.json から hook の登録が外されると、hook ごと効かなくなる。
登録が崩れたら、ここで赤にする。
"""


def test_guard_script_exists(guard_path):
    assert guard_path.is_file(), f"hook の本体がありません：{guard_path}"
