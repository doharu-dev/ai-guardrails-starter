# ai-guardrails-starter

AI に任せた開発を、人の目だけに頼らず**機械で止めて守る**ための雛形です。
危ない操作を実行前に止める hook、テストの書き換えを見つける CI、AI に渡す短い決めごと（rules）が入っています。
アプリのコード（会議室の予約が重なるかの判定）は題材で、自分のリポジトリには止める仕組みだけを持っていけば使えます。

## 中身

| ファイル | 役割 |
|---|---|
| `.claude/settings.json` | Claude Code に hook を登録する |
| `.claude/hooks/guard.sh` | 再帰的な削除・main への直接の push・hook 自身の書き換えを、実行前に止める |
| `.claude/rules/*.md` | AI に守ってほしい決めごと（1ファイル1テーマ） |
| `.github/workflows/test-tamper-check.yml` | PR でテストの既存の行が変わったら、理由が書かれるまで赤にする |
| `.github/workflows/ci.yml` | 整形の確認・lint・テスト |
| `CLAUDE.md` | AI 向けのリポジトリの地図 |
| `docs/demo.md` | 勉強会のデモの段取り |

hook は `bash` と `python3`（hook に渡される JSON を読むためだけに使う）を使います。`jq` は使いません。

## 入れ方

1. zip で受け取り、展開する。
2. 必要なファイルを自分のリポジトリの同じ場所に置く。
   - テストの書き換えの検知だけなら：`.github/workflows/test-tamper-check.yml`
   - hook も使うなら：`.claude/settings.json` と `.claude/hooks/guard.sh`。`.claude/settings.json` がすでにあれば、`hooks` の部分だけを足す。
   - rules も使うなら：`.claude/rules/` の中から必要なもの。
   - `ci.yml` は、自分のリポジトリの整形・lint・テストのコマンドに書き換えてから置く。
3. GitHub のリポジトリで、Settings → Actions → General を開き、Actions が動く設定になっていることを確かめる。
4. ブランチ保護で、`ci` と `test-tamper-check` を必須のチェックにする。
   1. Settings → Branches → Add branch protection rule（または Settings → Rules → Rulesets）を開く。
   2. 対象のブランチに `main` を指定する。
   3. 「Require a pull request before merging」と「Require status checks to pass before merging」に印を付ける。
   4. 必須にするチェックとして `ci` と `test-tamper-check` を選ぶ。
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

緑になっても、理由が正しいかどうかを決めるのは人です。この仕組みは「黙ってテストを書き換える」ことを止め、理由をレビューの場に出させるためのものです。

## つまずきやすい点

- **ブランチ保護は、無料プランの個人リポジトリでは公開リポジトリだけで使えます。** 非公開のままだと、チェックが赤でもマージできてしまいます。
- **zip では GitHub の設定は付いてきません。** Actions の有効化とブランチ保護は、リポジトリごとに自分で設定します。
- **最初から全部を止めないでください。** 止める仕組みを一度に増やすと、正しい作業まで止まって外したくなります。下の「入れる順番」で1つずつ足し、困ったところだけを止めます。
- hook を置いたあとは、Claude Code を起動し直すと確実に読み込まれます。
- hook はコマンドの文字列を見て判定するので、すべての書き方を止められるわけではありません。rules（`stop-and-report.md`）で「止められたら別の道を試さず報告する」と合わせて使います。

## 他の言語での使い方

`test-tamper-check.yml` の先頭にある `TEST_PATHS` を、自分のテストの場所に変えるだけで使えます。空白で区切ると複数書けます（git のパス指定の書き方）。

```yaml
env:
  TEST_PATHS: "src/test/"                          # Java（Maven・Gradle）
  # TEST_PATHS: ":(glob)**/*_test.go"              # Go
  # TEST_PATHS: ":(glob)src/**/*.test.ts __tests__/"  # TypeScript
```

hook（`guard.sh`）と rules は言語に関係なく使えます。`tests-are-not-edited.md` の `tests/`・`src/` は、自分のリポジトリの場所に書き換えてください。

## 入れる順番のおすすめ

1. **テストの書き換えの検知**（`test-tamper-check.yml`）：ファイル1つで始められ、効き目が一番わかりやすい。
2. **hook**（`.claude/settings.json`・`.claude/hooks/guard.sh`）：取り返しのつかない操作だけを止める。
3. **CI の段を増やす**（`ci.yml`）：整形 → lint → テスト、のように1段ずつ必須にしていく。

## 手元で動かす

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
ruff format --check . && ruff check . && pytest
```
