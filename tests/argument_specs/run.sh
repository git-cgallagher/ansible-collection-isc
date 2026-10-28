#!/usr/bin/env bash
# Argument-spec checks for every role in the collection:
#   1. check.py: each spec matches its role's defaults (names, types, choices, no_log)
#   2. ansible-doc loads each role's documentation
#   3. runtime.yml: each role rejects a bad value through its spec
# Requires: ansible-core, PyYAML. Run from anywhere.
set -euo pipefail
cd "$(dirname "$0")/../.."

python tests/argument_specs/check.py

# Expose this checkout as git_cgallagher.isc. A temp dir, because a committed
# directory symlink would fail ansible-test's symlinks check.
coll="$(mktemp -d)"
trap 'rm -rf "$coll"' EXIT
mkdir -p "$coll/ansible_collections/git_cgallagher"
ln -s "$(pwd)" "$coll/ansible_collections/git_cgallagher/isc"
export ANSIBLE_COLLECTIONS_PATH="$coll:${ANSIBLE_COLLECTIONS_PATH:-$HOME/.ansible/collections}"

for role in roles/*/; do
  role="$(basename "$role")"
  ansible-doc -t role "git_cgallagher.isc.$role" >/dev/null
  echo "ansible-doc: git_cgallagher.isc.$role OK"
  # A new role needs a bad-value case in runtime.yml too.
  if ! grep -q "argspec_role: $role[ ,}]" tests/argument_specs/runtime.yml; then
    echo "ERROR: tests/argument_specs/runtime.yml has no case for $role" >&2
    exit 1
  fi
done

ansible-playbook tests/argument_specs/runtime.yml
