{}:

let

common-src = builtins.fetchTarball {
    name = "common-2023-10-24";
    url = https://github.com/avanov/nix-common/archive/fdedd6a87d37972ca62ccfbe4f98190ed712a7bf.tar.gz;
    # Hash obtained using `nix-prefetch-url --unpack <url>`
    sha256 = "sha256:1cp1fp661a8dypyqb72yacg9av93g2xpw0sjnplss6swq3rgw7cy";
};

overlays = import ./overlays.nix {};
pkgs     = (import common-src { projectOverlays = [ overlays.globalPackageOverlay ]; }).pkgs;

in

{
    inherit pkgs;
}
