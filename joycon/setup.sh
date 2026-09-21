#!/bin/sh
set -eu
if [ "$(uname -s)" != Darwin ] || [ "$(uname -m)" != arm64 ]; then
	printf '%s\n' 'Apple Silicon macOS is required.' >&2
	exit 1
fi
if ! xcode-select -p >/dev/null 2>&1; then
	printf '%s\n' 'Install Xcode Command Line Tools first: xcode-select --install' >&2
	exit 1
fi
if ! command -v brew >/dev/null 2>&1; then
	printf '%s\n' 'Install Homebrew first: https://brew.sh/' >&2
	exit 1
fi
for formula in cmake python3 openssl@3 sdl3; do
	if ! brew list --versions "$formula" >/dev/null 2>&1; then
		brew install "$formula"
	fi
done
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
exec "$(brew --prefix)/bin/python3" "$script_dir/manage.py" setup "$@"
