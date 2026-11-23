{ pkgs, lib, ... }:

{
  environment.systemPackages = with pkgs; [
    nautilus
    sushi # Quick-look file previews
    gvfs  # Required for trash, mounting, and thumbnails
  ];
}
