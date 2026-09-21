#!/usr/bin/env python3
"""Build and stage the pinned client; profile activation is a separate operation."""
import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / 'joycon'


def run(*args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def output(*args):
    return subprocess.check_output([str(a) for a in args], text=True).strip()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_sources():
    lock = json.loads((HERE / 'source_lock.json').read_text())
    for relative, expected in lock['submodules'].items():
        path = ROOT / relative
        actual = output('git', '-C', path, 'rev-parse', 'HEAD')
        if actual != expected:
            raise ValueError(f'{relative}: expected {expected}, found {actual}')
        dirty = output('git', '-C', path, 'diff', '--name-only', '--ignore-submodules=all').splitlines()
        if dirty:
            # bionic contains case-only Linux header names. On macOS a checkout
            # can represent only one member of each pair. Accept only exact
            # tracked counterpart blobs, not arbitrary edits to those paths.
            tracked = output('git', '-C', path, 'ls-tree', '-r', '--name-only', 'HEAD').splitlines()
            for name in dirty:
                aliases = [other for other in tracked if other != name and other.casefold() == name.casefold()]
                actual_blob = output('git', '-C', path, 'hash-object', name)
                if not aliases or not any(actual_blob == output('git', '-C', path, 'rev-parse', 'HEAD:' + other) for other in aliases):
                    raise ValueError(f'{relative}/{name}: modified source')
            print(f'{relative}: verified {len(dirty)} case-colliding checkout paths')
        run('git', '-C', path, 'diff', '--cached', '--quiet', '--ignore-submodules=all')
    print(f"Verified {len(lock['submodules'])} pinned submodule commits")
    return lock


def build(args):
    if sys.platform != 'darwin' or output('uname', '-m') != 'arm64':
        raise ValueError('This recorded configuration targets Apple Silicon macOS')
    lock = verify_sources()
    openssl = args.openssl_root or Path(output('brew', '--prefix', 'openssl@3'))
    sdl = args.sdl3_dir or Path(output('brew', '--prefix', 'sdl3')) / 'lib/cmake/SDL3'
    build_dir = args.build_dir.resolve()
    run('cmake', '-S', ROOT, '-B', build_dir,
        '-DCMAKE_POLICY_VERSION_MINIMUM=3.5', '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
        '-DBUILD_UI=OFF', '-DBUILD_WEBVIEW=OFF', '-DGAMEWINDOW_SYSTEM=GLFW',
        '-DUSE_OWN_CURL=OFF', '-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0',
        '-DCMAKE_EXE_LINKER_FLAGS=-framework AppKit', '-DENABLE_DEV_PATHS=OFF',
        '-DSDL3_VENDORED=OFF', f'-DOPENSSL_ROOT_DIR={openssl}', f'-DSDL3_DIR={sdl}')
    run('cmake', '--build', build_dir, '--target', 'mcpelauncher-client', '-j', args.jobs)
    binary = build_dir / 'mcpelauncher-client/mcpelauncher-client'
    report = {'source_lock': lock, 'manifest_commit': output('git', '-C', ROOT, 'rev-parse', 'HEAD'),
              'binary_sha256': digest(binary), 'cmake': output('cmake', '--version').splitlines()[0],
              'clang': output('clang++', '--version').splitlines()[0],
              'macos': output('sw_vers', '-productVersion'),
              'sdk': output('xcrun', '--show-sdk-version'),
              'openssl': str(openssl), 'sdl3_dir': str(sdl),
              'runtime_tested': False}
    (build_dir / 'joycon_build_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Built {binary}; gameplay has not been tested by this command')


def parser_ini():
    config = configparser.RawConfigParser()
    config.optionxform = str
    return config


def write_private(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content.encode() if isinstance(content, str) else content)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def serialize(config):
    import io
    stream = io.StringIO()
    config.write(stream, space_around_delimiters=False)
    return stream.getvalue()


def profile(runtime, data_dir, mod):
    # QSettings INI escaping, then the launcher's quoted command-line parser.
    for path in (runtime, data_dir, mod):
        if any(c in str(path) for c in '\n\r"\\'):
            raise ValueError('Paths cannot contain quotes, backslashes, or newlines')
    template = (HERE / 'templates/profile.ini.in').read_text()
    template = template.replace('@RUNTIME@', str(runtime)).replace('@DATA_DIR@', str(data_dir)).replace('@UPDATE_MOD@', str(mod))
    config = parser_ini()
    config.read_string(template)
    return dict(config['Joy-Con-Keyboard'])


def package(args):
    verify_sources()
    dest = args.destination.resolve()
    if dest.exists():
        raise ValueError('Destination already exists; choose a NEW directory')
    binary = args.build_dir.resolve() / 'mcpelauncher-client/mcpelauncher-client'
    report = json.loads((args.build_dir / 'joycon_build_report.json').read_text())
    if digest(binary) != report['binary_sha256']:
        raise ValueError('Binary differs from build report')
    if report['source_lock'] != json.loads((HERE / 'source_lock.json').read_text()):
        raise ValueError('Source lock changed since build; rebuild before packaging')
    app = args.launcher_app.resolve() / 'Contents'
    mod = args.update_mod.resolve()
    data_dir = args.data_dir.expanduser().resolve()
    required = [app / 'Frameworks/mvk-angle/libEGL.dylib',
                app / 'Frameworks/mvk-angle/MoltenVK_icd.json',
                app / 'Resources/mcpelauncher/gamecontrollerdb.txt',
                app / 'MacOS/mcpelauncher-webview', app / 'MacOS/mcpelauncher-ui-qt',
                mod / 'libmcpelauncher-updates.so', mod / 'mod.json']
    for path in required:
        if not path.is_file():
            raise ValueError(f'Missing dependency: {path}')
    settings = profile(dest, data_dir, mod)
    dest.mkdir(parents=True)
    macos = dest / 'Contents/MacOS'
    macos.mkdir(parents=True)
    shutil.copy2(binary, macos / 'mcpelauncher_client')
    shutil.copytree(ROOT / 'mcpelauncher-mac-bin/lib', macos / 'lib')
    shutil.copy2(app / 'Resources/mcpelauncher/gamecontrollerdb.txt', macos / 'gamecontrollerdb.txt')
    for name in ('Frameworks', 'Resources'):
        (dest / 'Contents' / name).symlink_to(app / name, target_is_directory=True)
    for name in ('mcpelauncher-webview', 'mcpelauncher-ui-qt'):
        (macos / name).symlink_to(app / 'MacOS' / name)
    shutil.copy2(HERE / 'launch_client.sh', dest / 'launch_client.sh')
    (dest / 'launch_client.sh').chmod(0o755)
    (dest / 'version_metadata').mkdir()
    shutil.copy2(HERE / 'templates/version_metadata.json', dest / 'version_metadata/mod.json')
    config = parser_ini()
    config['Joy-Con-Keyboard'] = settings
    write_private(dest / 'profile.fragment.ini', serialize(config))
    shutil.copy2(args.build_dir / 'joycon_build_report.json', dest / 'build_report.json')
    licenses = dest / 'licenses'
    licenses.mkdir()
    shutil.copy2(ROOT / 'mcpelauncher-mac-bin/README.md', licenses / 'native_libraries_README.md')
    for name, source in [('manifest', ROOT), ('game_window', ROOT / 'game-window')]:
        for license_path in source.glob('LICENSE*'):
            shutil.copy2(license_path, licenses / (name + '_' + license_path.name))
    files = {str(p.relative_to(dest)): digest(p) for p in dest.rglob('*') if p.is_file() and not p.is_symlink()}
    write_private(dest / 'checksums.json', json.dumps(files, indent=2) + '\n')
    print(f'Staged {dest}; launcher profiles and worlds were NOT changed')


def apps_closed():
    names = output('ps', '-axo', 'comm=').splitlines()
    if any(Path(name.strip()).name.startswith(('mcpelauncher-client', 'mcpelauncher_client', 'mcpelauncher-ui')) for name in names):
        raise ValueError('Save and close Minecraft AND the launcher first')


def apply_profile(runtime, profiles_file, name):
    if not name or any(c in name for c in '[]/\\\n\r') or name in ('General', 'Metadata', 'DEFAULT'):
        raise ValueError('Invalid profile name')
    profiles_file = profiles_file.resolve()
    config = parser_ini()
    config.read(profiles_file)
    if name in config:
        raise ValueError('Profile already exists; choose a NEW profile name')
    fragment = parser_ini()
    fragment.read(runtime / 'profile.fragment.ini')
    entry = dict(fragment['Joy-Con-Keyboard'])
    if Path(entry['dataDir']).resolve() != profiles_file.parent.parent:
        raise ValueError('Profile dataDir must match the launcher data directory')
    receipts = runtime / 'profile_backups'
    receipts.mkdir(exist_ok=True)
    receipt_dir = Path(tempfile.mkdtemp(prefix='activation_', dir=receipts))
    existed = profiles_file.exists()
    backup = receipt_dir / 'profiles.before.ini'
    if existed:
        write_private(backup, profiles_file.read_bytes())
    config[name] = entry
    if 'General' not in config:
        config['General'] = {}
    config['General']['selected'] = name
    write_private(profiles_file, serialize(config))
    receipt = {'profiles_file': str(profiles_file), 'backup': str(backup), 'existed': existed,
               'installed_sha256': digest(profiles_file), 'profile': name}
    receipt_path = receipt_dir / 'receipt.json'
    write_private(receipt_path, json.dumps(receipt, indent=2) + '\n')
    return receipt_path


def restore_receipt(receipt_path):
    receipt = json.loads(receipt_path.read_text())
    target = Path(receipt['profiles_file'])
    if not target.is_file() or digest(target) != receipt['installed_sha256']:
        raise ValueError('Profiles changed since activation; refusing to overwrite newer edits')
    if receipt['existed']:
        write_private(target, Path(receipt['backup']).read_bytes())
    else:
        target.unlink()
    print('Restored previous profile configuration; runtime and worlds retained')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('verify')
    b = sub.add_parser('build')
    b.add_argument('--build-dir', type=Path, default=ROOT / 'build/joycon')
    b.add_argument('--jobs', default='8')
    b.add_argument('--openssl-root', type=Path)
    b.add_argument('--sdl3-dir', type=Path)
    p = sub.add_parser('package')
    p.add_argument('--build-dir', type=Path, default=ROOT / 'build/joycon')
    p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--launcher-app', type=Path, required=True)
    p.add_argument('--update-mod', type=Path, required=True)
    p.add_argument('--data-dir', type=Path, required=True)
    a = sub.add_parser('activate')
    a.add_argument('--runtime', type=Path, required=True)
    a.add_argument('--profiles-file', type=Path, required=True)
    a.add_argument('--name', default='Joy-Con-Keyboard-Rebuilt')
    r = sub.add_parser('restore')
    r.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        verify_sources()
    elif args.command == 'build':
        build(args)
    elif args.command == 'package':
        package(args)
    elif args.command == 'activate':
        apps_closed()
        print(apply_profile(args.runtime.resolve(), args.profiles_file, args.name))
    else:
        apps_closed()
        restore_receipt(args.receipt)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError, KeyError) as error:
        sys.exit(str(error))
