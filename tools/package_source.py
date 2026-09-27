"""Create a whitelist-only source archive without local experiments or run data."""
from pathlib import Path
import hashlib
import json
import zipfile

root=Path(__file__).resolve().parents[1]
top=("README.md","README.en.md","README.ja.md","LICENSE","THIRD_PARTY_NOTICES.md","CHANGELOG.md",
     "pyproject.toml","requirements-lock.txt",".gitignore",".gitattributes",".dockerignore","Dockerfile","compose.yaml","start.ps1","start.cmd")
files=[root/name for name in top]
allowed={".py",".js",".css",".html",".md",".yml",".csv",".json"}
for directory in ("hyperfit","tests","docs","examples","tools",".github"):
    files.extend(p for p in (root/directory).rglob("*") if p.is_file()
                 and p.suffix in allowed and "__pycache__" not in p.parts)
dist=root/"dist";dist.mkdir(exist_ok=True)
archive=dist/"HyperFit-0.1.0-source.zip"
manifest={str(p.relative_to(root)).replace("\\","/"):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files):z.write(p,"HyperFit-0.1.0/"+p.relative_to(root).as_posix())
    z.writestr("HyperFit-0.1.0/SOURCE-MANIFEST.json",json.dumps(manifest,indent=2))
print(json.dumps({"archive":str(archive),"files":len(files),"bytes":archive.stat().st_size,
                  "sha256":hashlib.sha256(archive.read_bytes()).hexdigest()},indent=2))
