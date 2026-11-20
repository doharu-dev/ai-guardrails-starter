# ai-guardrails-starter

AI に任せた開発を、人の目だけに頼らず**機械で止めて守る**ための雛形です。
危ない操作を実行前に止める hook、テストの書き換えを見つける CI、AI に渡す短い決めごと（rules）、そしてそれらの仕組みが崩れていないかを確かめるテストが入っています。
アプリのコード（会議室の予約が重なるかの判定）は題材で、自分のリポジトリには止める仕組みだけを持っていけば使えます。

## 中身

| ファイル | 役割 |
|---|---|
| `.claude/settings.json` | Claude Code に hook を登録する |
| `.claude/hooks/guard.sh` | 再帰的な削除・main への直接の push・hook 自身（`.claude/hooks/`）の書き換え・hook の登録（`.claude/settings.json`）の書き換えを、実行前に止める |
| `.claude/rules/*.md` | AI に守ってほしい決めごと（1ファイル1テーマ） |
| `.github/workflows/test-tamper-check.yml` | PR でテストの既存の行が変わったり、テストを無効にする書き方（skip など）が足されたりしたら、理由が書かれるまで赤にする |
| `.github/scripts/check_test_tamper.py` | `test-tamper-check` の判定の本体（Python の標準ライブラリだけで動く） |
| `.github/workflows/guardrails.yml` | 仕組みを守るテスト（`tests/guardrails/`）だけを流す |
| `tests/guardrails/` | hook・hook の登録・テストの書き換えの検知が、崩れていないかを確かめるテスト |
| `.github/workflows/ci.yml` | 整形の確認・lint・テスト |
| `CLAUDE.md` | AI 向けのリポジトリの地図 |
| `docs/demo.md` | 勉強会のデモの段取り |

hook は `bash` と `python3`（hook に渡される JSON を読むためだけに使う）を使います。`jq` は使いません。

## 入れ方

1. zip で受け取り、展開する。
2. 必要なファイルを自分のリポジトリの同じ場所に置く。
   - テストの書き換えの検知だけなら：`.github/workflows/test-tamper-check.yml` と `.github/scripts/check_test_tamper.py`
   - hook も使うなら：`.claude/settings.json` と `.claude/hooks/guard.sh`。`.claude/settings.json` がすでにあれば、`hooks` の部分だけを足す。
   - 仕組みを守るテストも使うなら：`.github/workflows/guardrails.yml` と `tests/guardrails/`（使わない仕組みのテストファイルは消してよい）
   - rules も使うなら：`.claude/rules/` の中から必要なもの。
   - `ci.yml` は、自分のリポジトリの整形・lint・テストのコマンドに書き換えてから置く。pytest を使うなら、`tests/guardrails/` は `guardrails` のジョブが流すので `--ignore=tests/guardrails` で外す。
3. GitHub のリポジトリで、Settings → Actions → General を開き、Actions が動く設定になっていることを確かめる。
4. ブランチ保護で、`ci`・`test-tamper-check`・`guardrails` を必須のチェックにする。
   1. Settings → Branches → Add branch protection rule（または Settings → Rules → Rulesets）を開く。
   2. 対象のブランチに `main` を指定する。
   3. 「Require a pull request before merging」と「Require status checks to pass before merging」に印を付ける。
   4. 必須にするチェックとして `ci`・`test-tamper-check`・`guardrails` を選ぶ。
      チェックは一度でも動いたことがないと候補に出ないので、先に PR を1つ出して動かしておく。

## 試し方

1. 作業用のブランチを作り、`tests/` の既存の行を1行消してコミットし、PR を出す。
2. `test-tamper-check` が赤くなり、マージのボタンが押せないことを見る。
   ログには、見つかったファイルと削除行の数、通す方法が出ます。
3. PR 本文に次を足して保存する。保存すると自動で判定し直し、緑になる。

   ```markdown
   ## テストを変えた理由
   （なぜ既存のテストを変える必要があったか）
   ```

テストを消す代わりに skip を足しても同じように赤になります。たとえば既存のテストに `@pytest.mark.skip` を足すと、ログに次のように出ます。

```text
テストを無効にする書き方が足されています：
  - tests/test_booking.py:9  @pytest.mark.skip(reason='later')
```

緑になっても、理由が正しいかどうかを決めるのは人です。この仕組みは「黙ってテストを書き換える」ことを止め、理由をレビューの場に出させるためのものです。

## つまずきやすい点

- **ブランチ保護は、無料プランの個人リポジトリでは公開リポジトリだけで使えます。** 非公開のままだと、チェックが赤でもマージできてしまいます。
- **zip では GitHub の設定は付いてきません。** Actions の有効化とブランチ保護は、リポジトリごとに自分で設定します。
- **最初から全部を止めないでください。** 止める仕組みを一度に増やすと、正しい作業まで止まって外したくなります。下の「入れる順番」で1つずつ足し、困ったところだけを止めます。
- hook を置いたあとは、Claude Code を起動し直すと確実に読み込まれます。
- hook はコマンドの文字列を見て判定するので、すべての書き方を止められるわけではありません（たとえば `python3` のスクリプトの中からファイルを書き換えるのは止められません）。rules（`stop-and-report.md`）で「止められたら別の道を試さず報告する」と合わせて使います。
- 仕組みを守るテストが確かめるのは、リポジトリに入っているものだけです。個人の設定（`.claude/settings.local.json` やホームの `~/.claude/settings.json`）で hook を止める設定をされると、CI からは見えません。

## 仕組みを守るテスト（guardrails）

止める仕組みは、誰かが（人でも AI でも）少し書き換えるだけで、黙って効かなくなります。
`tests/guardrails/` のテストは、次のことを CI（`guardrails` のジョブ）で毎回確かめ、崩れたら赤にします。

| テスト | 確かめること |
|---|---|
| `test_hook_registration.py` | `.claude/settings.json` の PreToolUse に、`guard.sh` が Bash・Edit・Write を見張る形で登録されている |
| `test_hook_behavior.py` | `guard.sh` が4つの操作を止め（終了コード 2）、作業ブランチへの push・`src/` の編集・ファイル1つの削除・`.claude/settings.local.json` の編集などは通す（終了コード 0） |
| `test_tamper_check.py` | `check_test_tamper.py` が、テストの変更・skip の追加・理由の有無の組み合わせを正しく判定する |

`guardrails` のジョブは Python と pytest だけを入れ、`tests/guardrails/pytest.ini` の設定で動きます。
プロジェクトの言語や依存、`pyproject.toml` には左右されないので、Java や Go のリポジトリにもそのまま置けます。
ファイルの場所（`settings.json`・`guard.sh` など）は `tests/guardrails/conftest.py` の先頭にまとめてあります。

### `guardrails` が赤になったら

| 赤になったテスト | 考えられること | 直す場所 |
|---|---|---|
| `test_guard_is_registered_for_bash_edit_write` | hook の登録が外された、または見張る道具が減った | `.claude/settings.json` の `hooks` を元に戻す |
| `test_guard_denies` | 止めるべき操作を `guard.sh` が止めなくなった | `.claude/hooks/guard.sh` |
| `test_guard_allows` | `guard.sh` が普通の操作まで止めるようになった | `.claude/hooks/guard.sh` |
| `test_guard_has_no_variable_followed_by_wide_char` | `"$x（"` のように、変数のすぐ後ろに全角の文字がある（macOS の bash で hook が落ちる） | `.claude/hooks/guard.sh` で `${x}` と囲む |
| `test_tamper_check.py` | テストの書き換えの検知が変わった | `.github/scripts/check_test_tamper.py` |

`.claude/hooks/` と `.claude/settings.json` は hook が AI の書き換えを止めるので、直すのは人です。

止める操作を**わざと**変えたとき（rules を変えた、守るブランチの名前を変えた、など）は、テストの側を合わせます。
`test_hook_behavior.py` の `DENY`・`ALLOW` に足すだけなら、そのまま通ります。
既存の行を変えたり消したりすると `test-tamper-check` が赤になるので、PR 本文の「## テストを変えた理由」に理由を書きます。

## 他の言語での使い方

`test-tamper-check.yml` の先頭にある `TEST_PATHS` を、自分のテストの場所に変えるだけで使えます。空白で区切ると複数書けます（git のパス指定の書き方）。
**`tests/guardrails/` は必ず残してください。** 外すと、仕組みを守るテストを黙って消したり skip したりできてしまいます。

```yaml
env:
  TEST_PATHS: "src/test/ tests/guardrails/"                       # Java（Maven・Gradle）
  # TEST_PATHS: ":(glob)**/*_test.go tests/guardrails/"           # Go
  # TEST_PATHS: ":(glob)src/**/*.test.ts __tests__/ tests/guardrails/"  # TypeScript
```

テストを無効にする書き方は、`.github/scripts/check_test_tamper.py` の先頭の `SKIP_PATTERNS`（正規表現のリスト）で決めています。
最初は Python（pytest・unittest）の書き方だけが入っています。他の言語では、コメントにある例を参考に足してください。

```python
SKIP_PATTERNS = [
    r"pytest\.mark\.skip(if)?\b",
    r"pytest\.mark\.xfail\b",
    r"pytest\.skip\(",
    r"unittest\.skip",
    r"\b(it|test|describe)\.skip\b",  # 例：JavaScript / TypeScript を足した
]
```

足したら、`tests/guardrails/test_tamper_check.py` にその書き方が赤になるテストを足すと安心です。

hook（`guard.sh`）と rules は言語に関係なく使えます。`tests-are-not-edited.md` の `tests/`・`src/` は、自分のリポジトリの場所に書き換えてください。

## 入れる順番のおすすめ

1. **テストの書き換えの検知**（`test-tamper-check.yml`）：ファイル1つで始められ、効き目が一番わかりやすい。
2. **hook**（`.claude/settings.json`・`.claude/hooks/guard.sh`）：取り返しのつかない操作だけを止める。
3. **仕組みを守るテスト**（`guardrails.yml`・`tests/guardrails/`）：1と2が黙って外されたり壊れたりしないようにする。
4. **CI の段を増やす**（`ci.yml`）：整形 → lint → テスト、のように1段ずつ必須にしていく。

## 手元で動かす

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
ruff format --check . && ruff check . && pytest

# 仕組みを守るテストだけを、CI の guardrails と同じ形で流す
python -m pytest -c tests/guardrails/pytest.ini tests/guardrails
```
