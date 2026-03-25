#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: concat_nt.sh [--force] <input_dir> [output_file]

Concatenate all .nt files from <input_dir> in lexicographic order and write
one gzip-compressed output file.

Arguments:
  input_dir    Directory containing .nt files.
  output_file  Optional output path. Default: <input_dir>/triples.gz

Options:
  -f, --force  Overwrite output file if it already exists.
  -h, --help   Show this help message.
EOF
}

force=0

while (($#)); do
  case "$1" in
    -f|--force)
      force=1
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

cleanup() {
  rm -f "$list_file" "$tmp_output"
}
trap cleanup EXIT

find "$input_dir" -maxdepth 1 -type f -name '*.nt' -print0 | sort -z > "$list_file"

if [[ ! -s "$list_file" ]]; then
  echo "Error: no .nt files found in: $input_dir" >&2
  exit 1
fi

xargs -0 cat < "$list_file" | gzip -n -c > "$tmp_output"

if [[ $force -eq 1 ]]; then
  rm -f "$output_file"
fi

mv "$tmp_output" "$output_file"

echo "Wrote: $output_file"
