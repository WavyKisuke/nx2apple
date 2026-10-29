#!/usr/bin/env python3
"""Build a synthetic production iOS project to validate the iOS toolchain.

This intentionally does not require proprietary game data. The generated IPA is
an unsigned CI fixture, not a runnable game distribution.
"""
from pathlib import Path
import argparse
import shutil
import subprocess


def run(cmd, cwd=None):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.output)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    project = root / "project"
    app = project / "DmIOS"
    app.mkdir(parents=True)

    (app / "main.m").write_text(
        '#import <UIKit/UIKit.h>\n'
        'int main(int argc,char **argv){ @autoreleasepool { '
        'return UIApplicationMain(argc,argv,nil,nil); } }\n'
    )
    (app / "Info.plist").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>'
        '<key>CFBundleIdentifier</key><string>org.nxnative.ci.app</string>'
        '<key>CFBundleExecutable</key><string>DmIOS</string>'
        '<key>CFBundleName</key><string>DmIOS</string>'
        '<key>CFBundlePackageType</key><string>APPL</string>'
        '<key>CFBundleShortVersionString</key><string>1.0</string>'
        '<key>CFBundleVersion</key><string>1</string>'
        '<key>UILaunchStoryboardName</key><string></string>'
        '</dict></plist>\n'
    )

    # Keep the CI fixture completely self-contained. In particular, never copy
    # dm/*.fixups.tsv or other rewritten-module output from the source tree.
    xcodeproj = project / "project.yml"
    xcodeproj.write_text(
        'name: DmIOS\n'
        'settings:\n'
        '  base:\n'
        '    IPHONEOS_DEPLOYMENT_TARGET: 15.0\n'
        'targets:\n'
        '  DmIOS:\n'
        '    type: application\n'
        '    platform: iOS\n'
        '    sources:\n'
        '      - DmIOS\n'
        '    settings:\n'
        '      base:\n'
        '        PRODUCT_BUNDLE_IDENTIFIER: org.nxnative.ci.app\n'
        '        INFOPLIST_FILE: DmIOS/Info.plist\n'
        '        CODE_SIGNING_ALLOWED: NO\n'
        '        CODE_SIGNING_REQUIRED: NO\n'
    )

    run(["xcodegen", "generate"], cwd=project)
    run([
        "xcodebuild", "-project", "DmIOS.xcodeproj", "-scheme", "DmIOS",
        "-sdk", "iphoneos", "-configuration", "Release",
        "CODE_SIGNING_ALLOWED=NO", "CODE_SIGNING_REQUIRED=NO",
        "BUILD_DIR=" + str(root / "build"),
    ], cwd=project)

    products = root / "build" / "Release-iphoneos"
    ipa_root = root / "Payload"
    ipa_root.mkdir()
    shutil.copytree(products / "DmIOS.app", ipa_root / "DmIOS.app")

    # Defensive verification: the synthetic fixture must not contain rewritten
    # game modules. A real game build uses patch_nso.py + gen_embed.py instead.
    for p in ipa_root.rglob("*"):
        if p.is_file() and (p.name.endswith(".fixups.tsv") or p.name.endswith(".patched.bin")):
            raise RuntimeError(f"synthetic IPA unexpectedly contains rewritten module output: {p}")

    ipa = root / "DmIOS-CI-synthetic.ipa"
    shutil.make_archive(str(ipa.with_suffix("")), "zip", root, "Payload")
    zip_path = ipa.with_suffix(".zip")
    zip_path.rename(ipa)
    print(ipa)


if __name__ == "__main__":
    main()
