# このリポジトリの地図

AI に任せた開発を、人の目だけに頼らず機械で止めるための雛形です。
主役は止める仕組み（rules・hook・CI）で、`src/booking.py`（会議室の予約が重なるかの判定）は題材にすぎません。

## 必ず通すコマンド

作業を終える前に、次の3つがすべて通ること。CI（`.github/workflows/ci.yml`）も同じものを動かします。

```sh
ruff format --check .
ruff check .
pytest
```

## どこに何があるか

| 場所 | 中身 |
|---|---|
| `.claude/rules/` | 守ってほしい決めごと。1ファイル1テーマ。決めごとはここにだけ書く |
| `.claude/settings.json`・`.claude/hooks/guard.sh` | 危ない操作を実行前に止める hook |
| `.github/workflows/` | `ci`（整形・lint・テスト）と `test-tamper-check`（テストの書き換えの検知） |
| `src/`・`tests/` | 題材のコードとテスト |
| `docs/demo.md` | 勉強会のデモの段取り |
