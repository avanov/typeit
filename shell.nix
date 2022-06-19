{
    pkgs ? (import (builtins.fetchGit {
        url = "https://github.com/avanov/nix-common.git";
        ref = "master";
        rev = "be2dc05bf6beac92fc12da9a2adae6994c9f2ee6";
    }) {}).pkgs
,   pyVersion ? "310"
,   isDevEnv  ? true
}:

let

    python = pkgs."python${pyVersion}";
    pythonPkgs = pkgs."python${pyVersion}Packages";
    devLibs = if isDevEnv then [ pythonPkgs.twine pythonPkgs.wheel ] else [ pythonPkgs.coveralls ];
in

# Make a new "derivation" that represents our shell
pkgs.mkShellNoCC {
    name = "typeit";

    # The packages in the `buildInputs` list will be added to the PATH in our shell
    # Python-specific guide:
    # https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/python.section.md
    nativeBuildInputs = with pkgs; [
        # see https://nixos.org/nixos/packages.html
        # Python distribution
        python
        pythonPkgs.virtualenv
        ncurses
        libxml2
        libxslt
        libzip
        zlib
        which
    ] ++ devLibs;
    shellHook = ''
        # set SOURCE_DATE_EPOCH so that we can use python wheels
        export SOURCE_DATE_EPOCH=$(date +%s)

        export VENV_DIR="$PWD/.venv${pyVersion}"

        export PATH=$VENV_DIR/bin:$PATH
        export PYTHONPATH=""
        export LANG=en_US.UTF-8

        # https://python-poetry.org/docs/configuration/
        export PIP_CACHE_DIR="$PWD/.local/pip-cache${pyVersion}"

        # Setup virtualenv
        if [ ! -d $VENV_DIR ]; then
            virtualenv $VENV_DIR
            pip install -r requirements/minimal.txt
            pip install -r requirements/test.txt
            pip install -r requirements/extras/third_party.txt
        fi
    '';
}