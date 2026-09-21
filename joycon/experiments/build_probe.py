#!/usr/bin/env python3
"""Build an isolated Joy-Con diagnostic; never modify the pinned checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def run(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path,
                        help='Existing, initialized and clean manifest checkout')
    parser.add_argument('--destination', required=True, type=Path,
                        help='NEW directory for the source copy and build')
    parser.add_argument('--cached-deps', type=Path,
                        help='Existing CMake _deps directory with GLFW and JSON sources')
    parser.add_argument('--jobs', type=int, default=10)
    args = parser.parse_args()
    source, dest = args.source.resolve(), args.destination.resolve()
    lock = json.loads((HERE.parent / 'source_lock.json').read_text())
    if json.loads((source / 'joycon/source_lock.json').read_text()) != lock:
        parser.error('Source lock differs from the recorded baseline')
    if dest.exists() or source == dest or source in dest.parents:
        parser.error('Destination must be NEW and outside the source checkout')
    run(sys.executable, source / 'joycon/manage.py', 'verify')
    dest.mkdir(parents=True)
    copied = dest / 'source'
    shutil.copytree(source, copied, ignore=shutil.ignore_patterns('.git', 'build', '.local', '__pycache__'))
    patches = [('game-window', 'game-window-probe.patch'),
               ('mcpelauncher-client', 'client-joystick-source.patch')]
    for module, patch in patches:
        with (HERE / patch).open() as f:
            run('patch', '-p1', cwd=copied / module, stdin=f)
    openssl = subprocess.check_output(['brew', '--prefix', 'openssl@3'], text=True).strip()
    sdl = subprocess.check_output(['brew', '--prefix', 'sdl3'], text=True).strip()
    configure = ['cmake', '-S', copied, '-B', dest / 'build',
                 '-DCMAKE_POLICY_VERSION_MINIMUM=3.5', '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
                 '-DBUILD_UI=OFF', '-DBUILD_WEBVIEW=OFF', '-DGAMEWINDOW_SYSTEM=GLFW',
                 '-DUSE_OWN_CURL=OFF', '-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0',
                 '-DCMAKE_EXE_LINKER_FLAGS=-framework AppKit', '-DENABLE_DEV_PATHS=OFF',
                 '-DSDL3_VENDORED=OFF', '-DUSE_GAMECONTROLLERDB=OFF',
                 f'-DOPENSSL_ROOT_DIR={openssl}', f'-DSDL3_DIR={sdl}/lib/cmake/SDL3']
    if args.cached_deps:
        deps = args.cached_deps.resolve()
        for dep in ('glfw3_ext', 'nlohmann_json_ext'):
            path = deps / (dep + '-src')
            if not (path / 'CMakeLists.txt').is_file():
                parser.error(f'Missing cached dependency: {path}')
            configure.append(f'-DFETCHCONTENT_SOURCE_DIR_{dep.upper()}={path}')
    run(*configure)
    run('cmake', '--build', dest / 'build', '--target', 'mcpelauncher-client', '-j', args.jobs)
    binary = dest / 'build/mcpelauncher-client/mcpelauncher-client'
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    evidence = {'source_lock': lock, 'binary_sha256': digest(binary),
                'patch_sha256': {p: digest(HERE / p) for _, p in patches}, 'runtime_tested': False}
    (dest / 'build-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(f'Built diagnostic binary: {binary}')


if __name__ == '__main__':
    main()
