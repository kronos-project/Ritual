#!/usr/bin/env bash
# usage: ./decode.sh assets   ->  writes to assets-decoded/
# Disclaimer: Used as a developer aid. LLM generated.
set -u

types="assets/types/defaults-no-windows.json"
src="${1%/}"
dst="${src}-deserialized"

# every directory that directly contains at least one .xml
find "$src" -type f -name '*.xml' -printf '%h\0' | sort -zu | while IFS= read -r -d '' d; do
    rel="${d#"$src"}"; rel="${rel#/}"
    outdir="$dst${rel:+/$rel}"
    mkdir -p "$outdir"

    files=("$d"/*.xml)
    if [ "${#files[@]}" -eq 1 ]; then
        # single match: -o must be a file path
        katsuba op -t "$types" de "${files[0]}" -o "$outdir/$(basename "${files[0]}")"
    else
        # quoted so katsuba expands the glob itself (no arg-length limit)
        katsuba op -t "$types" de "$d/*.xml" -o "$outdir"
    fi && echo "DONE: $d (${#files[@]} files)" || echo "FAILED: $d" >&2
done

python3 - "$types" "$dst" <<'PY'
import json, re, sys
from pathlib import Path

types, dst = sys.argv[1], Path(sys.argv[2])
names = {v["hash"]: re.sub(r"^(class|struct|enum) ", "", v["name"])
         for v in json.load(open(types))["classes"].values()}

def resolve(o):
    if isinstance(o, dict):
        return {k: (names.get(v, v) if k == "$__type" and isinstance(v, int) else resolve(v))
                for k, v in o.items()}
    if isinstance(o, list):
        return [resolve(x) for x in o]
    return o

done = 0
for p in sorted(dst.rglob("*")):
    if not p.is_file():
        continue
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        p.write_text(json.dumps(resolve(data), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        done += 1
    except Exception as ex:
        print(f"FORMAT FAILED: {p}: {ex}", file=sys.stderr)
print(f"FORMATTED: {done} files")
PY