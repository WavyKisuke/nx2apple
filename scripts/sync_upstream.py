#!/usr/bin/env python3
"""Sync this fork with upstream seedds/nxnative.

The fork was started as a fresh repository (no shared git history), so GitHub's own
"Sync fork" does not apply. The sync is a mechanical procedure — take upstream's tree,
re-apply the fork's features, verify the result builds — and this script is that
procedure, so a scheduled CI job can run it unattended.

What it does:
  1. diffs the two upstream refs over the vendored paths (dm/ scripts/ docs/ AGENTS.md ref/), and
     adds any vendored file upstream has that the fork's tree lacks
  2. applies adds and modifications file by file, and deletions — except the fork's own
     files (the RomFS archive layer), which upstream must not delete
  3. re-applies the fork's patches to the files that carry them (PATCHED; one patcher each, in
     PATCHERS, with a marker only the fork's code contains); every patch is anchor-based and
     idempotent, and one that no longer fits fails the run loudly rather than producing a silently
     broken tree. Before any of that, check_unprotected() stops the run when a vendored file the
     fork edited by hand (it differs from the last sync base) is in none of OURS, PATCHED and
     DROPPED and upstream changes it now: the edit would be lost.
  4. verifies: every .py parses on the Python this fork supports as its floor (3.9),
     the iOS build script survives bash -n, the archive reader test passes, and the
     macOS host builds for a real profile (skippable with --skip-build)

On success the caller commits and pushes; on failure nothing is written outside the
working tree, so CI can open an issue with the log instead.

Every patcher is also run against the files of a real upstream ref by scripts/tests/test_sync_patchers.py
(CI, and locally with seedds/main fetched), so a patcher that no longer fits, or whose marker upstream's
own text satisfies, fails there before it can stop or silently skip a sync (issue #92).

Usage: sync_upstream.py --old <upstream sha> --new <upstream sha> [--skip-build]
       sync_upstream.py --old <last sync base> --check-protection   (list unprotected fork edits)
"""
import argparse, json, os, pwd, re, subprocess, sys, shutil, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VENDORED = ('dm', 'scripts', 'docs', 'AGENTS.md', 'ref')
# The fork's own files, inside vendored paths: upstream deletes and rewrites must not touch them.
OURS = {'dm/host/romfs_arc.c', 'dm/host/romfs_arc.h', 'dm/tools/romfs_arc.py',
        'dm/host/tests/t_romfs_arc.c', 'docs/ROMFS_ARCHIVE.md',
        'dm/games/0100A00019DE0000/game.fork.tsv',
        # BC decode for GPUs without BC support (from d2r-mobile's bcdec line; tex_bc_cpu profiles)
        'dm/third_party/bcdec/bcdec.h', 'dm/third_party/bcdec/LICENSE',
        'dm/gfx/tex/nvn_bcdec.c', 'dm/gfx/tex/nvn_bcdec.h',
        'dm/gfx/tex/tests/t_bcdec.c',
        # The Mac front end's key and controller button map (seedds/nxnative#386, still open):
        # the launcher's Controls page writes DM_KEYMAP / DM_PAD_MAP, and patch_front_mac() makes
        # front_mac.m read them. Fork-only until #386 merges, so a sync must not delete them.
        'dm/host/input_map.h',
        'dm/host/tests/t_input_map.c',
        'dm/host/tests/t_launcher_contract.c',
        # The Increased Memory Limit guide the README links to; upstream has no such file, and the
        # first wholesale sync deleted it.
        'dm/ios/ENTITLEMENTS.md',
        # Fork-only workflow smoke helper used to produce a compile/link fixture on GitHub's macOS runner.
        'dm/ios/tools/build_smoke.py',
        # This script: fork-only, so a PR that changes it is not a vendored edit (pr-scope reads OURS)
        'scripts/sync_upstream.py', 'scripts/tests/test_sync_patchers.py',
        'dm/tools/tests/test_nro_header.py',
        'dm/ios/Sources/DataBookmark.m', 'dm/ios/Sources/DataBookmark.h'}
PATCHED = ('dm/host/hle_fs.c', 'dm/host/Makefile', 'dm/host/tests/Makefile', 'dm/ios/tools/build_ipa.sh',
           'scripts/build_ipa_from_nsp.py',
           'dm/ios/Sources/main.m', 'dm/gfx/nvn/nvn_mtl.m', 'dm/host/dm.h',
           'dm/ios/tests/test_romfs_startup.py', 'dm/ios/tests/test_profile_pack.py', 'docs/env_switches.tsv', 'dm/host/front_mac.m', 'dm/tools/patch_nso.py', 'dm/games/0100A00019DE0000/game.tsv',
           'dm/mac/launcher.c', 'dm/host/hle_svc.c', 'dm/host/hle_os.c', 'dm/host/hle_fpslock.c', 'dm/host/loader.c',
           'dm/ios/Sources/DmGamepad.m', 'dm/ios/Sources/Launcher.swift', 'dm/ios/project.yml',
           'dm/ios/tests/test_xcode_workflow.py', 'dm/tools/env_switches.py', 'dm/tools/tests/test_env_switches.py',
           'dm/tools/impact_map.tsv', 'dm/games/game.py', 'dm/games/0100F2C0115B6000/game.tsv',
           'docs/agents/README.md', 'docs/development.md')

def git(*a):
    r = subprocess.run(['git', *a], cwd=REPO, capture_output=True, text=True)
    if r.returncode: sys.exit(f'git {" ".join(a)} failed: {r.stderr.strip()}')
    return r.stdout

def blob(rev, path):
    r = subprocess.run(['git', 'cat-file', 'blob', f'{rev}:{path}'], cwd=REPO, capture_output=True)
    return r.stdout if r.returncode == 0 else None

def upstream_changes(old, new):
    """(kind, path) for every vendored file that differs."""
    out = git('diff', '--name-status', old, new, '--', *VENDORED).splitlines()
    changes = []
    for line in out:
        parts = line.split('\t', 1)
        if len(parts) == 2:
            changes.append(tuple(parts))
    return changes
