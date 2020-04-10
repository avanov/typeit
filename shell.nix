with (import (builtins.fetchTarball {
  # Descriptive name to make the store path easier to identify
  name = "typeit-python38";
  # Commit hash for nixos-unstable as of 2019-10-27
  url = https://github.com/NixOS/nixpkgs-channels/archive/f601ab37c2fb7e5f65989a92df383bcd6942567a.tar.gz;
  # Hash obtained using `nix-prefetch-url --unpack <url>`
  sha256 = "0ikhcmcc29iiaqjv5r91ncgxny2z67bjzkppd3wr1yx44sv7v69s";
}) {});

# Make a new "derivation" that represents our shell
stdenv.mkDerivation {
    name = "typeit38";

    # The packages in the `buildInputs` list will be added to the PATH in our shell
    # Python-specific guide:
    # https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/python.section.md
    buildInputs = [
        # see https://nixos.org/nixos/packages.html
        # Python distribution
        python38Full
        python38Packages.virtualenv
        python38Packages.wheel
        python38Packages.twine
        taglib
        ncurses
        libxml2
        libxslt
        libzip
        zlib
        # root CA certificates
        cacert
        which
    ];
    shellHook = ''
        # set SOURCE_DATE_EPOCH so that we can use python wheels
        export SOURCE_DATE_EPOCH=$(date +%s)

        VENV_DIR=$PWD/.venv

        export PATH=$VENV_DIR/bin:$PATH
        export PYTHONPATH=""
        export LANG=en_US.UTF-8

        # https://python-poetry.org/docs/configuration/
        export PIP_CACHE_DIR=$PWD/.local/pip-cache

        # Setup virtualenv
        if [ ! -d $VENV_DIR ]; then
            virtualenv $PWD/.venv
        fi
    '';
}