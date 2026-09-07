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
in
pkgs.writeText "gramlab-runtime.json" (
  builtins.toJSON {
    schema = 1;
    bubblewrap = "${pkgs.bubblewrap}/bin/bwrap";
    python = "${python}/bin/python3";
    storePaths = "${closure}/store-paths";
    inherit executables environment posixShell;
  }
)
