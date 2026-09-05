{
  pkgs,
  nixpkgs,
  profile,
}:
let
  inherit (pkgs) lib;
  upstreamRepo = lib.importJSON (nixpkgs + "/pkgs/development/mobile/androidenv/repo.json");
  # Google's official archive uses this CDN. Preserve the pinned archive names and hashes;
  # provisioning must not depend on a particular developer's proxy or SDK Manager state.
  repo = lib.mapAttrsRecursive (
    path: value:
    if lib.last path == "archives" then
      map (
        archive:
        archive
        // {
          url =
            lib.replaceStrings
              [ "https://dl.google.com/android/repository/" ]
              [ "https://redirector.gvt1.com/edgedl/android/repository/" ]
              archive.url;
        }
      ) value
    else
      value
  ) upstreamRepo;
  image = repo.images.${profile.sdk.platform}.${profile.runtime.imageType}.${profile.runtime.abi};
  composition = pkgs.androidenv.composeAndroidPackages {
    inherit repo;
    cmdLineToolsVersion = profile.sdk.commandLineTools;
    platformToolsVersion = profile.sdk.platformTools;
    buildToolsVersions = [ profile.sdk.buildTools ];
    platformVersions = [ profile.sdk.platform ];
    toolsVersion = null;
    includeEmulator = true;
    emulatorVersion = profile.runtime.emulator;
    includeSystemImages = true;
    systemImageTypes = [ profile.runtime.imageType ];
    abiVersions = [ profile.runtime.abi ];
    includeSources = false;
    includeNDK = true;
    ndkVersions = [ profile.sdk.ndk ];
    includeCmake = true;
    cmakeVersions = [ profile.sdk.cmake ];
  };
  sdk = composition.androidsdk.overrideAttrs (previous: {
    postInstall = (previous.postInstall or "") + ''
      # Modern SDK tools otherwise discover the same NDK twice and report inconsistent metadata.
      test -L "$out/libexec/android-sdk/ndk-bundle"
      rm "$out/libexec/android-sdk/ndk-bundle"
    '';
  });
in
# Image package names encode the API/ABI, not the image revision. Refuse silent drift on upgrades.
assert image.revision-details."major:0" == toString profile.runtime.imageRevision;
assert image.type-details."extension-level:1" == toString profile.runtime.imageExtensionLevel;
assert (builtins.head image.archives).sha1 == profile.provenance.imagePublishedSha1;
{
  inherit composition sdk;
  home = "${sdk}/libexec/android-sdk";
}
