#!/usr/bin/env bash
# Claude Code の PreToolUse hook。危ない操作を実行前に止める。
#
# 止める操作は次の3つだけ。
#   1. 再帰的な削除（rm -r・rm -rf など）                  … Bash
#   2. main への直接の push                                 … Bash
#   3. .claude/hooks/ 配下の書き換え（hook 自身を外させない）… Edit・Write・Bash
#
# 受け取り方：標準入力に JSON（tool_name・tool_input・cwd など）が来る。
# 止め方    ：理由と代わりの行動を標準エラーに書き、終了コード 2 で終わる。
#             Claude Code はこの文面を AI に渡し、操作は実行されない。
# 通す      ：何も出さずに終了コード 0 で終わる。
#
# 前提：bash と python3（JSON を読むためだけに使う）。

set -u

PROTECTED_BRANCH="main"
HOOKS_DIR=".claude/hooks"

deny() {
  # $1: 止めた理由 / $2: 代わりにしてほしいこと
  {
    echo "[guard.sh] この操作は hook で止めました。"
    echo "止めた理由：$1"
    echo "代わりに：$2"
    echo "別のやり方で同じ結果を出そうとせず、このメッセージを人に報告してください。"
  } >&2
  exit 2
}

# ---- 標準入力の JSON を読む ----------------------------------------------
input="$(cat)"

if ! command -v python3 >/dev/null 2>&1; then
  deny "python3 が見つからず、操作が安全か確かめられません。" \
    "python3 を入れるよう人に頼んでください。"
fi

# field tool_input.command のように、ドットでたどった文字列の値を返す
field() {
  printf '%s' "$input" | python3 -c '
import json, sys
value = json.load(sys.stdin)
for key in sys.argv[1].split("."):
    value = value.get(key, "") if isinstance(value, dict) else ""
print(value if isinstance(value, str) else "", end="")
' "$1" 2>/dev/null
}

tool_name="$(field tool_name)" || deny "hook に渡された JSON を読めませんでした。" \
  "操作の内容を人に伝え、人に実行してもらってください。"

# ---- Edit・Write：.claude/hooks/ 配下の書き換え ---------------------------
if [[ "$tool_name" == "Edit" || "$tool_name" == "Write" ]]; then
  file_path="$(field tool_input.file_path)"
  if [[ "$file_path" == *"/$HOOKS_DIR/"* || "$file_path" == "$HOOKS_DIR/"* ]]; then
    deny "$HOOKS_DIR/ は AI を止める仕組みそのもので、AI が書き換えると止める意味がなくなります。（対象：$file_path）" \
      "変えたい内容と理由を人に伝え、人に書き換えてもらってください。"
  fi
  exit 0
fi

[[ "$tool_name" == "Bash" ]] || exit 0

# ---- Bash：コマンドを「;・&・|・括弧・改行」で区切って1つずつ見る ----------
command_text="$(field tool_input.command)"
cwd="$(field cwd)"

current_branch() {
  git -C "${cwd:-.}" symbolic-ref --short HEAD 2>/dev/null
}

# 区切った1つ分のコマンドについて、先頭の sudo・env などを飛ばした単語の位置を返す
first_word_index() {
  local -a w=("$@")
  local i=0
  while ((i < ${#w[@]})); do
    case "${w[i]}" in
      sudo | env | command | exec | nohup | time | xargs | *=*) ((i++)) ;;
      *) break ;;
    esac
  done
  echo "$i"
}

check_recursive_rm() {
  local -a w=("$@")
  local i
  i="$(first_word_index "$@")"
  [[ "${w[i]:-}" == "rm" || "${w[i]:-}" == */rm ]] || return 0
  for ((i = i + 1; i < ${#w[@]}; i++)); do
    [[ "${w[i]}" == "--" ]] && break
    if [[ "${w[i]}" == "--recursive" || "${w[i]}" =~ ^-[a-zA-Z]*[rR] ]]; then
      deny "再帰的な削除（rm -r など）は、消してはいけないものまで一度に消えるおそれがあります。" \
        "消したいファイルやフォルダを一覧にして人に見せ、人に消してもらってください。"
    fi
  done
}

check_push_to_main() {
  local -a w=("$@")
  local i
  i="$(first_word_index "$@")"
  [[ "${w[i]:-}" == "git" || "${w[i]:-}" == */git ]] || return 0
  # git と push の間のオプション（-C dir・-c key=value など）を飛ばす
  for ((i = i + 1; i < ${#w[@]}; i++)); do
    case "${w[i]}" in
      -C | -c) ((i++)) ;;
      -*) ;;
      *) break ;;
    esac
  done
  [[ "${w[i]:-}" == "push" ]] || return 0

  local -a positional=()
  for ((i = i + 1; i < ${#w[@]}; i++)); do
    case "${w[i]}" in
      --all | --mirror)
        deny "${w[i]} はすべてのブランチを push するため、$PROTECTED_BRANCH にも直接 push されます。" \
          "作業用のブランチだけを push し（git push origin <作業ブランチ>）、プルリクエストを出してください。" ;;
      -*) ;;
      *) positional+=("${w[i]}") ;;
    esac
  done

  # 1つ目は push 先のリモート、2つ目以降が refspec（src:dst）
  local -a refspecs=("HEAD")
  ((${#positional[@]} > 1)) && refspecs=("${positional[@]:1}")

  local spec dst
  for spec in "${refspecs[@]}"; do
    spec="${spec#+}"
    dst="${spec##*:}"
    [[ "$dst" == "HEAD" ]] && dst="$(current_branch)"
    dst="${dst#refs/heads/}"
    if [[ "$dst" == "$PROTECTED_BRANCH" ]]; then
      deny "$PROTECTED_BRANCH への直接の push は、レビューと CI を通らずに変更が入ります。" \
        "作業用のブランチに push し（git push origin <作業ブランチ>）、プルリクエストを出してください。"
    fi
  done
}

check_hooks_rewrite() {
  local segment="$1"
  shift
  [[ "$segment" == *"$HOOKS_DIR"* ]] || return 0
  local -a w=("$@")
  local i
  i="$(first_word_index "$@")"
  local cmd="${w[i]:-}"
  cmd="${cmd##*/}"
  local last="${w[${#w[@]} - 1]}"
  local rewrite=""
  case "$cmd" in
    rm | mv | unlink | truncate | chmod | chown | touch | tee) rewrite="yes" ;;
    cp | ln | install | rsync) [[ "$last" == *"$HOOKS_DIR"* ]] && rewrite="yes" ;;
    sed | perl) [[ "$segment" =~ [[:space:]]-[a-zA-Z]*i ]] && rewrite="yes" ;;
    git) [[ "${w[i + 1]:-}" =~ ^(rm|mv|checkout|restore|apply)$ ]] && rewrite="yes" ;;
  esac
  # リダイレクト（> や >>）の書き込み先が .claude/hooks/ 配下
  if [[ "$segment" =~ \>[[:space:]]*[^[:space:]]*\.claude/hooks ]]; then
    rewrite="yes"
  fi
  if [[ -n "$rewrite" ]]; then
    deny "$HOOKS_DIR/ は AI を止める仕組みそのもので、AI が書き換えると止める意味がなくなります。" \
      "変えたい内容と理由を人に伝え、人に書き換えてもらってください。"
  fi
}

while IFS= read -r segment; do
  read -r -a words <<<"$segment" || true
  ((${#words[@]} > 0)) || continue
  check_recursive_rm "${words[@]}"
  check_push_to_main "${words[@]}"
  check_hooks_rewrite "$segment" "${words[@]}"
done < <(printf '%s\n' "$command_text" | tr ';&|()`' '\n\n\n\n\n\n')

exit 0
