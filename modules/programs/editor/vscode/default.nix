{ lib, pkgs, ... }:
{
  nixpkgs.config.allowUnfreePredicate = pkg: builtins.elem (lib.getName pkg) [ "vscode" ];

  home-manager.sharedModules = [
    (
      { config, ... }:
      let
        dir = "${config.home.homeDirectory}/NixOS/modules/programs/editor/vscode";
        link = config.lib.file.mkOutOfStoreSymlink;
      in
      {
        programs.vscode = {
          enable = true;
          mutableExtensionsDir = true;
          package = pkgs.vscode;
          profiles.default.extensions = with pkgs.vscode-extensions; [
            bbenoist.nix
            arrterian.nix-env-selector
            eamodio.gitlens
            github.vscode-github-actions
            yzhang.markdown-all-in-one
            catppuccin.catppuccin-vsc
            catppuccin.catppuccin-vsc-icons
            jnoortheen.nix-ide
          ];
          # NOTE: no userSettings / keybindings here, otherwise the module
          # also generates a store-backed settings.json and conflicts.
        };

        xdg.configFile."Code/User/settings.json".source = link "${dir}/settings.json";
        xdg.configFile."Code/User/keybindings.json".source = link "${dir}/keybindings.json";
      }
    )
  ];
}
