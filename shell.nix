with (import (builtins.fetchTarball {
  # Descriptive name to make the store path easier to identify
  name = "typeit-python38";
  # Commit hash for nixos-unstable as of 2019-10-27
  url = https://github.com/NixOS/nixpkgs/archive/4aaf2ad527e123e99ecb993130e8458125a6a42f.tar.gz;
  # Hash obtained using `nix-prefetch-url --unpack <url>`
  sha256 = "0h9lbijvzbm30dlzm7y4v6iah5d8bxbw8i6ipsfy6fapyf2l79z0";
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

        virtualenv $PWD/.venv
        export PATH=$PWD/.venv/bin:$PATH

        export LANG=en_US.UTF-8
    '';
}