#!/usr/bin/env bash
# Runs a command in the ansible-runtime image (ghcr.io/git-cgallagher/ansible-runtime),
# the pinned toolchain the CI jobs share: ansible-core, ansible-lint, yamllint, Molecule
# with the molecule-git-cgallagher driver, the Python libraries and the third-party
# collections. The image is the pin: these jobs install nothing themselves.
#   RUNTIME_IMAGE=ghcr.io/git-cgallagher/ansible-runtime:X.Y.Z-ci@sha256:... .github/ci/runtime.sh molecule test
#
# Why `docker run` and not a `container:` job: the repo is mounted at the SAME path and
# the container shares the runner's network. Tests here bind-mount checkout files into
# containers they start (tests/kea_dhcp/validate.py) and reach published ports on
# 127.0.0.1 (the Stork scenarios); both break when the controller sits on its own
# network with the checkout at /__w.
set -euo pipefail
: "${RUNTIME_IMAGE:?set RUNTIME_IMAGE (ansible-test.yml sets it)}"
root=$(git rev-parse --show-toplevel)

# Temporary files go under the checkout too (.cache/ is gitignored): validate.py mounts
# files from mkdtemp() into `docker run`, and the daemon can't see the container's /tmp.
tmp="$root/.cache/tmp"
mkdir -p "$tmp"

# Molecule runs the roles as git_cgallagher.isc.<role>; the base config's
# ANSIBLE_COLLECTIONS_PATH puts .molecule-collections (gitignored) first.
if [ "${1:-}" = molecule ]; then
  mkdir -p "$root/.molecule-collections/ansible_collections/git_cgallagher"
  ln -sfn ../../.. "$root/.molecule-collections/ansible_collections/git_cgallagher/isc"
fi

# The checkout belongs to the runner's user and the image runs as root, so git (which
# ansible-lint uses to list files) needs the checkout marked safe.
exec docker run --rm --network host \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$root:$root" -w "$PWD" -e TMPDIR="$tmp" \
  -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0='*' \
  -e PY_COLORS -e ANSIBLE_FORCE_COLOR -e GITHUB_ACTIONS \
  "$RUNTIME_IMAGE" "$@"
