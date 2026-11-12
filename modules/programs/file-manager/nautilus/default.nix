{ pkgs, lib, ... }:


environment.systemPackages = with pkgs; [
  nautilus
  gnome.sushi # Optional: quick-look previews
  gvfs # Recommended for trash, mounting, and thumbnails
];
