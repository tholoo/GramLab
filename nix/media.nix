{ pkgs, nixpkgs }:
pkgs.writeText "gramlab-media-toolchain.json" (
  builtins.toJSON {
    schema = 1;
    nixpkgs_revision = nixpkgs.rev;
    package = "ffmpeg_6";
    versions = {
      ffmpeg = pkgs.ffmpeg_6.version;
      libvpx = pkgs.libvpx.version;
      libwebp = pkgs.libwebp.version;
    };
    executables = {
      ffmpeg = "${pkgs.ffmpeg_6}/bin/ffmpeg";
      ffprobe = "${pkgs.ffmpeg_6}/bin/ffprobe";
    };
  }
)
