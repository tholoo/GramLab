{
  pkgs,
  extraPackages ? [ ],
  executables ? { },
  environment ? { },
  posixShell ? null,
}:
let
  python = pkgs.python313.withPackages (packages: [ packages.pillow ]);
  closure = pkgs.closureInfo {
    rootPaths = [
      python
      pkgs.bubblewrap
    ]
    ++ extraPackages;
  };
  supervisorClosure = pkgs.closureInfo {
    rootPaths = [
      python
      pkgs.bubblewrap
      pkgs.ffmpeg_6
    ]
    ++ extraPackages;
  };
in
pkgs.writeText "gramlab-runtime.json" (
  builtins.toJSON {
    schema = 1;
    bubblewrap = "${pkgs.bubblewrap}/bin/bwrap";
    python = "${python}/bin/python3";
    storePaths = "${closure}/store-paths";
    supervisorStorePaths = "${supervisorClosure}/store-paths";
    inherit executables environment posixShell;
    supervisorEnvironment = {
      GRAMLAB_FFMPEG = "${pkgs.ffmpeg_6}/bin/ffmpeg";
      GRAMLAB_FFPROBE = "${pkgs.ffmpeg_6}/bin/ffprobe";
    };
  }
)
