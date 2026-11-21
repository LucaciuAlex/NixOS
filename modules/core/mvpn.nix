{ host, pkgs, ... }:

let
  inherit (import ../../hosts/${host}/variables.nix) hostname;
in
{

  services.tailscale = {
    # Enable tailscale at startup
    enable = true;

  };

}
