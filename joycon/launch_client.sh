#!/bin/sh
set -eu
if [ "$#" -lt 1 ]; then
	printf '%s\n' 'Launch using the generated launcher profile.' >&2
	exit 2
fi
# %command% supplies the original executable, followed by Minecraft arguments.
shift
runtime_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
umask 077
if [ -f "$runtime_dir/runtime.log" ]; then
	mv "$runtime_dir/runtime.log" "$runtime_dir/runtime.previous.log"
fi
exec "$runtime_dir/Contents/MacOS/mcpelauncher_client" "$@" >"$runtime_dir/runtime.log" 2>&1
