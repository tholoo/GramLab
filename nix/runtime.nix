{
  pkgs,
  extraPackages ? [ ],
  executables ? { },
  environment ? { },
  posixShell ? null,
}:
let
  closure = pkgs.closureInfo { rootPaths = [ pkgs.python313 ] ++ extraPackages; };
in
pkgs.writeText "gramlab-runtime.json" (
  builtins.toJSON {
    schema = 1;
    bubblewrap = "${pkgs.bubblewrap}/bin/bwrap";
    python = "${pkgs.python313}/bin/python3";
    storePaths = "${closure}/store-paths";
    inherit executables environment posixShell;
  }
)
