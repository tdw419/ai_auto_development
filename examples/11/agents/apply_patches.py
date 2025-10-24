#!/usr/bin/env python3
import sys, json, subprocess, tempfile, os

baton = json.loads(open(sys.argv[1]).read())
patches = baton.get("patch_bundle",[])
if not patches: sys.exit(0)

with tempfile.NamedTemporaryFile("w", delete=False) as f:
    for p in patches:
        f.write(p["diff"] + ("\n" if not p["diff"].endswith("\n") else ""))
    tmp = f.name

# dry-run then apply
subprocess.check_call(["git","apply","--check",tmp])
subprocess.check_call(["git","apply",tmp])