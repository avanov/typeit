{}:

let

globalPackageOverlay = (self: original: rec {
    # Place overrides here as described in https://nixos.wiki/wiki/Overlays#Examples_of_overlays
});

in

{
    inherit globalPackageOverlay;
}
