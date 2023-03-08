{}:

let

common-src = builtins.fetchTarball {
    name = "common-2023-03-03";
    url = https://github.com/avanov/nix-common/archive/a30f466f3ac73842d111e80f40f287d8aa13e929.tar.gz;
    # Hash obtained using `nix-prefetch-url --unpack <url>`
    sha256 = "sha256:1dimd334ay4jx4n81n5ms8p4i9kpyn0z7mm8xa0kcy2cpdlbq798";
};

overlays = import ./overlays.nix {};
pkgs     = (import common-src { projectOverlays = [ overlays.globalPackageOverlay ]; }).pkgs;

in

{
    inherit pkgs;
}
