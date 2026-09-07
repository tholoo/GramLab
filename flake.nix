{
  description = "GramLab: reproducible Python development and isolated Android preparation";

  # Intentional upgrades change this revision and regenerate flake.lock together with the
  # Android provenance checks. No registry or developer-local NIX_PATH is used.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/9387b3fcc0c23c86661636da63faabad4235a0a6";

  outputs =
    { nixpkgs, ... }:
    let
      inherit (nixpkgs) lib;
      profile = lib.importJSON ./clients/android/toolchain.json;
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
      ];
      forAllSystems = lib.genAttrs systems;
      packagesFor =
        system:
        import nixpkgs {
          inherit system;
          config = {
            # Approval is scoped to the SDK packages, not every unfree package in nixpkgs.
            allowUnfreePredicate =
              package: (package.meta.homepage or null) == "https://developer.android.com/tools";
            android_sdk.accept_license = true;
          };
        };
      formatSource = lib.fileset.toSource {
        root = ./.;
        fileset = lib.fileset.unions [
          ./flake.nix
          ./nix
        ];
      };
      commonShell =
        pkgs:
        {
          packages =
            with pkgs;
            [
              python313
              uv
              git
              curl
              jq
              ripgrep
              nixfmt
              shellcheck
            ]
            ++ lib.optionals pkgs.stdenv.hostPlatform.isLinux [
              util-linux
              iproute2
            ];
          UV_PYTHON = "${pkgs.python313}/bin/python3";
          UV_PYTHON_DOWNLOADS = "never";
          shellHook = ''
            export GRAMLAB_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
            export UV_PROJECT_ENVIRONMENT="$GRAMLAB_ROOT/.venv"
            export UV_CACHE_DIR="$GRAMLAB_ROOT/.cache/uv"
            mkdir -p "$UV_CACHE_DIR"
          '';
        }
        // lib.optionalAttrs pkgs.stdenv.hostPlatform.isLinux {
          GRAMLAB_RUNTIME_PROFILE = import ./nix/runtime.nix { inherit pkgs; };
        };
    in
    {
      formatter = forAllSystems (
        system:
        (packagesFor system).nixfmt-tree.override {
          settings.excludes = [
            "clients/android/upstream/**"
            ".cache/**"
            "artifacts/**"
          ];
        }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = packagesFor system;
          common = commonShell pkgs;
          jdk = pkgs."jdk${toString profile.jvm.major}";
          android = import ./nix/android.nix { inherit pkgs nixpkgs profile; };
          androidRuntimeTools = with pkgs; [
            bash
            coreutils
            gnused
            gawk
          ];
        in
        {
          default = pkgs.mkShellNoCC (common // { name = "gramlab-core"; });
          media = pkgs.mkShellNoCC (
            common
            // {
              name = "gramlab-media";
              packages = common.packages ++ [ pkgs.ffmpeg_6 ];
              GRAMLAB_MEDIA_TOOLCHAIN = import ./nix/media.nix { inherit pkgs nixpkgs; };
            }
          );
        }
        // lib.optionalAttrs (system == profile.runtime.hostSystem) {
          android = pkgs.mkShell (
            common
            // {
              name = "gramlab-android";
              packages =
                common.packages
                ++ (with pkgs; [
                  android.sdk
                  jdk
                  gnumake
                  pkg-config
                  ninja
                  unzip
                  zip
                ]);
              JAVA_HOME = jdk.home;
              ANDROID_HOME = android.home;
              ANDROID_SDK_ROOT = android.home;
              ANDROID_NDK_HOME = "${android.home}/ndk/${profile.sdk.ndk}";
              ANDROID_NDK_ROOT = "${android.home}/ndk/${profile.sdk.ndk}";
              GRAMLAB_ANDROID_RUNTIME_PROFILE = import ./nix/runtime.nix {
                inherit pkgs;
                posixShell = "${pkgs.bash}/bin/sh";
                extraPackages = [
                  android.sdk
                  jdk
                ]
                ++ androidRuntimeTools;
                executables = {
                  emulator = "${android.home}/emulator/emulator";
                  adb = "${android.home}/platform-tools/adb";
                  avdmanager = "${android.home}/cmdline-tools/${profile.sdk.commandLineTools}/bin/avdmanager";
                };
                environment = {
                  JAVA_HOME = jdk.home;
                  ANDROID_HOME = android.home;
                  ANDROID_SDK_ROOT = android.home;
                  ANDROID_USER_HOME = "/work/android";
                  ANDROID_AVD_HOME = "/work/android/avd";
                  HOME = "/work/home";
                  XDG_CACHE_HOME = "/work/cache";
                  PATH = lib.makeBinPath (androidRuntimeTools ++ [ jdk ]);
                };
              };
              shellHook = common.shellHook + ''
                export GRADLE_USER_HOME="$GRAMLAB_ROOT/.cache/gradle"
                export ANDROID_USER_HOME="$GRAMLAB_ROOT/.cache/android"
                export ANDROID_AVD_HOME="$ANDROID_USER_HOME/avd"
                export PATH="${android.home}/cmake/${profile.sdk.cmake}/bin:$PATH"
                export GRADLE_OPTS="''${GRADLE_OPTS:+$GRADLE_OPTS }-Dorg.gradle.project.android.aapt2FromMavenOverride=${android.home}/build-tools/${profile.sdk.buildTools}/aapt2"
                mkdir -p "$GRADLE_USER_HOME" "$ANDROID_USER_HOME" "$ANDROID_AVD_HOME"
              '';
            }
          );
        }
      );

      packages.${profile.runtime.hostSystem}.android-sdk =
        (import ./nix/android.nix {
          pkgs = packagesFor profile.runtime.hostSystem;
          inherit nixpkgs profile;
        }).sdk;

      checks = forAllSystems (
        system:
        let
          pkgs = packagesFor system;
        in
        {
          nix-format =
            pkgs.runCommand "gramlab-nix-format"
              {
                nativeBuildInputs = [ pkgs.nixfmt ];
              }
              ''
                nixfmt --check ${formatSource}/flake.nix ${formatSource}/nix/*.nix
                touch "$out"
              '';
          direnv-syntax =
            pkgs.runCommand "gramlab-direnv-syntax"
              {
                nativeBuildInputs = [
                  pkgs.bash
                  pkgs.shellcheck
                ];
              }
              ''
                bash -n ${./.envrc}
                shellcheck --shell=bash ${./.envrc}
                touch "$out"
              '';
          workflow =
            pkgs.runCommand "gramlab-workflow"
              {
                nativeBuildInputs = [
                  pkgs.actionlint
                  pkgs.shellcheck
                ];
              }
              ''
                actionlint ${./.github/workflows/quality.yml}
                touch "$out"
              '';
        }
      );
    };
}
