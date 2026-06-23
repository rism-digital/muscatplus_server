#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: concat_nt.sh [--force] [--dedup] <input_dir> [output_file]

Concatenate all .nt files from <input_dir> in lexicographic order and write
one gzip-compressed output file.

Arguments:
  input_dir    Directory containing .nt files.
  output_file  Optional output path. Default: <input_dir>/triples.gz

Options:
  -f, --force  Overwrite output file if it already exists.
  --dedup      Remove exact duplicate lines with GNU sort before compression.
               This reorders output lexicographically.
  --no-progress
               Disable progress display even when 'pv' is installed.
  -h, --help   Show this help message.
EOF
}

force=0
dedup=0
show_progress=1

detect_gnu_sort() {
  local uname_s
  uname_s=$(uname -s)

  if [[ "$uname_s" == "Darwin" ]]; then
    if ! command -v gsort >/dev/null 2>&1; then
      echo "Error: --dedup requires GNU sort; install 'gsort' on macOS." >&2
      exit 1
    fi
    echo "gsort"
    return
  fi

  if ! command -v sort >/dev/null 2>&1; then
    echo "Error: sort not found." >&2
    exit 1
  fi

  if ! sort --version >/dev/null 2>&1; then
    echo "Error: --dedup requires GNU sort; current 'sort' does not support --version." >&2
    exit 1
  fi

  if ! sort --version 2>/dev/null | grep -qi "GNU coreutils"; then
    echo "Error: --dedup requires GNU sort." >&2
    exit 1
  fi

  echo "sort"
}

while (($#)); do
  case "$1" in
    -f|--force)
      force=1
      shift
      ;;
    --dedup)
      dedup=1
      shift
      ;;
    --no-progress)
      show_progress=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 2
fi

input_dir=$1
output_file=${2:-"$input_dir/triples.gz"}

if [[ ! -d "$input_dir" ]]; then
  echo "Error: input directory does not exist: $input_dir" >&2
  exit 1
fi

if [[ -e "$output_file" && $force -ne 1 ]]; then
  echo "Error: output file already exists: $output_file" >&2
  echo "Use --force to overwrite." >&2
  exit 1
fi

output_dir=$(dirname "$output_file")
mkdir -p "$output_dir"

list_file=$(mktemp "${TMPDIR:-/tmp}/concat-nt-list.XXXXXX")
tmp_output=$(mktemp "$output_dir/.triples.gz.tmp.XXXXXX")
sort_tmpdir=""
sort_bin=""

cleanup() {
  rm -f "$list_file" "$tmp_output"
  if [[ -n "$sort_tmpdir" ]]; then
    rm -rf "$sort_tmpdir"
  fi
}
trap cleanup EXIT

find "$input_dir" -maxdepth 2 -type f -name '*.nt' -print0 | sort -z > "$list_file"

if [[ ! -s "$list_file" ]]; then
  echo "Error: no .nt files found in: $input_dir" >&2
  exit 1
fi

file_count=$(tr -cd '\0' < "$list_file" | wc -c | tr -d ' ')

if stat -f %z "$output_dir" >/dev/null 2>&1; then
  total_bytes=$(xargs -0 stat -f %z < "$list_file" | awk '{s+=$1} END{print s+0}')
else
  total_bytes=$(xargs -0 stat -c %s < "$list_file" | awk '{s+=$1} END{print s+0}')
fi

echo "Found $file_count .nt files (${total_bytes} bytes total)." >&2
echo "Compressing to: $output_file" >&2

if [[ $dedup -eq 1 ]]; then
  sort_bin=$(detect_gnu_sort)
  mkdir -p "$input_dir/tmp"
  sort_tmpdir=$(mktemp -d "$input_dir/tmp/concat-nt-sort.XXXXXX")

  echo "De-duplication enabled: removing exact duplicate lines." >&2
  echo "Output order will be lexicographic." >&2
  echo "Using GNU sort binary: $sort_bin" >&2
  echo "Using GNU sort buffer size: 50%" >&2
  echo "Using GNU sort temp directory: $sort_tmpdir" >&2
fi

if [[ $show_progress -eq 1 ]] && command -v pv >/dev/null 2>&1; then
  if [[ $dedup -eq 1 ]]; then
    xargs -0 cat < "$list_file" \
      | pv -f -p -t -e -r -b -s "$total_bytes" \
      | LC_ALL=C "$sort_bin" -u -S 50% -T "$sort_tmpdir" \
      | gzip -n -c > "$tmp_output"
  else
    xargs -0 cat < "$list_file" \
      | pv -f -p -t -e -r -b -s "$total_bytes" \
      | gzip -n -c > "$tmp_output"
  fi
else
  if [[ $show_progress -eq 1 ]]; then
    echo "Note: 'pv' not found; running without live ETA/progress." >&2
  fi
  if [[ $dedup -eq 1 ]]; then
    xargs -0 cat < "$list_file" \
      | LC_ALL=C "$sort_bin" -u -S 50% -T "$sort_tmpdir" \
      | gzip -n -c > "$tmp_output"
  else
    xargs -0 cat < "$list_file" | gzip -n -c > "$tmp_output"
  fi
fi

if [[ $force -eq 1 ]]; then
  rm -f "$output_file"
fi

mv "$tmp_output" "$output_file"

if stat -f %z "$output_file" >/dev/null 2>&1; then
  out_size=$(stat -f %z "$output_file")
else
  out_size=$(stat -c %s "$output_file")
fi

echo "Wrote: $output_file (${out_size} bytes)" >&2
