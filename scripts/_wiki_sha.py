import hashlib
from pathlib import Path

WIKI = Path(r"D:\工作\SCDC数据日常工作\llm-wiki\wiki")
src = WIKI / "sources" / "article-20261101-chan-quant-bsp-ml-evidence.md"
text = src.read_text(encoding="utf-8")
sha = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16].upper()
lines = text.splitlines(keepends=True)
for i, ln in enumerate(lines[:15]):
    if ln.startswith("sha256:"):
        lines[i] = f"sha256: {sha}\n"
        break
src.write_text("".join(lines), encoding="utf-8", newline="\n")
log = WIKI / "log.md"
with log.open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n- 2026-11-03 ingest-update sources/article-20261101-chan-quant-bsp-ml-evidence.md — 追加实验 #31-#33（尾部标签 ML：事件级阳性/组合级第四次死亡；铁律终版）；sha256={sha}\n")
print("sha256:", sha)
