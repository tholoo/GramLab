{ pkgs }:
let
  closure = pkgs.closureInfo { rootPaths = [ pkgs.python313 ]; };
in
pkgs.writeText "gramlab-runtime.json" (
  builtins.toJSON {
    schema = 1;
    bubblewrap = "${pkgs.bubblewrap}/bin/bwrap";
    python = "${pkgs.python313}/bin/python3";
    storePaths = "${closure}/store-paths";
  }
)
