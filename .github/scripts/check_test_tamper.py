"""テストの書き換えを検知する（.github/workflows/test-tamper-check.yml から呼ぶ）。

PR の分岐点から head までの差分で、見張る場所（TEST_PATHS）に次のどちらかがあれば、
PR 本文に「## テストを変えた理由」の見出しと本文が無いかぎり失敗（終了コード 1）にする。

- 既存の行の変更・削除（削除行）
- テストを無効にする書き方を足した行（SKIP_PATTERNS に当たる追加行）

テストを足すだけなら通す。標準ライブラリだけで動く（プロジェクトの言語に関係なく使える）。

環境変数：
  TEST_PATHS  見張る場所。空白区切りの git のパス指定（例 "tests/" や ":(glob)**/*_test.go"）
  BASE_SHA    PR の base の commit
  HEAD_SHA    PR の head の commit
  PR_BODY     PR 本文（run に直接埋め込まず、環境変数で渡す）
"""

import os
import re
import subprocess
import sys

# テストを無効にする書き方（正規表現）。追加行がこれに当たると、削除行と同じ扱いにする。
# 他の言語では、ここに足す。例：
#   JavaScript / TypeScript：r"\b(it|test|describe)\.skip\b"、r"\bx(it|describe)\("
#   Java（JUnit）          ：r"@Disabled\b"、r"@Ignore\b"
#   Go                     ：r"\bt\.Skip(f|Now)?\("
SKIP_PATTERNS = [
    r"pytest\.mark\.skip(if)?\b",
    r"pytest\.mark\.xfail\b",
    r"pytest\.skip\(",
    r"unittest\.skip",
]

REASON_HEADING = "## テストを変えた理由"


def diff_lines(base: str, head: str, paths: list[str]) -> tuple[dict[str, int], list[tuple]]:
    """削除行の数（ファイルごと）と、追加行（ファイル・行番号・中身）を返す。"""
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "diff", "--unified=0", "--find-renames"]
        + [f"{base}...{head}", "--"]
        + paths,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    deleted: dict[str, int] = {}
    added: list[tuple[str, int, str]] = []
    old_path = new_path = ""
    new_line = 0
    for line in out.splitlines():
        if line.startswith("diff --git "):
            m = re.match(r"diff --git a/(.+) b/(.+)$", line)
            old_path, new_path = m.groups() if m else ("", "")
        elif line.startswith("--- "):
            old_path = line[6:] if line.startswith("--- a/") else ""
        elif line.startswith("+++ "):
            new_path = line[6:] if line.startswith("+++ b/") else ""
        elif line.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            new_line = int(m.group(1)) if m else 0
        elif line.startswith("Binary files"):
            # 中身を読めないファイルの変更は、削除行があるものとして扱う
            name = new_path or old_path
            deleted[name] = deleted.get(name, 0) + 1
        elif line.startswith("-"):
            name = new_path or old_path
            deleted[name] = deleted.get(name, 0) + 1
        elif line.startswith("+"):
            added.append((new_path, new_line, line[1:]))
            new_line += 1
    return deleted, added


def find_skips(added: list[tuple[str, int, str]]) -> list[tuple[str, int, str]]:
    """追加行のうち、テストを無効にする書き方に当たるものを返す。"""
    patterns = [re.compile(p) for p in SKIP_PATTERNS]
    return [a for a in added if any(p.search(a[2]) for p in patterns)]


def has_reason(body: str) -> bool:
    """PR 本文に「## テストを変えた理由」の見出しがあり、その下に本文があるか。

    HTML コメントと空行だけなら、本文なしとみなす。
    """
    body = body.replace("\r\n", "\n")
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    m = re.search(
        rf"^{re.escape(REASON_HEADING)}[ \t]*$(.*?)(?=^#{{1,2}} |\Z)", body, flags=re.M | re.S
    )
    return bool(m and m.group(1).strip())


def main() -> int:
    paths = os.environ.get("TEST_PATHS", "").split()
    if not paths:
        print("::error::TEST_PATHS が空です。見張るテストの場所を書いてください。")
        return 1
    print(f"見張る場所：{' '.join(paths)}")

    deleted, added = diff_lines(os.environ["BASE_SHA"], os.environ["HEAD_SHA"], paths)
    skips = find_skips(added)

    if not deleted and not skips:
        print("テストの既存の行は変わっていません（変更なし、または追加だけ）。")
        return 0

    if deleted:
        print("テストの既存の行が変わっています：")
        for name, count in deleted.items():
            print(f"  - {name}（削除行 {count}）")
    if skips:
        print("テストを無効にする書き方が足されています：")
        for name, line_no, text in skips:
            print(f"  - {name}:{line_no}  {text.strip()}")

    if has_reason(os.environ.get("PR_BODY", "")):
        print(f"PR 本文に「{REASON_HEADING}」があるので通します。")
        print("レビューでその理由を確かめてください。")
        return 0

    print(
        "::error title=test-tamper-check::テストの既存の行の変更や、テストを無効にする書き方の"
        "追加がありますが、PR 本文に理由がありません。"
    )
    print("通す方法：PR 本文に次の見出しを足し、その下に理由を書いて保存してください。")
    print("保存すると自動で判定し直します。")
    print("")
    print(f"  {REASON_HEADING}")
    print("  （なぜ既存のテストを変える・無効にする必要があったか）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
