{
  inputs,
  pkgs,
  ...
}:
let
  uniclipboardPackage = inputs.uniclipboard.packages.${pkgs.stdenv.hostPlatform.system}.default;
  waitForKeyring = pkgs.writeShellScript "uniclipboard-autostart" ''
    while true; do
      collection="$(${pkgs.systemd}/bin/busctl --user --quiet call \
      org.freedesktop.secrets \
      /org/freedesktop/secrets \
      org.freedesktop.Secret.Service ReadAlias s default \
      2>/dev/null | ${pkgs.coreutils}/bin/cut -d '"' -f 2)"
      if [ -n "$collection" ] && [ "$(${pkgs.systemd}/bin/busctl --user --quiet get-property \
        org.freedesktop.secrets \
        "$collection" \
        org.freedesktop.Secret.Collection Locked \
        2>/dev/null)" = "b false" ]; then
        break
      fi
      ${pkgs.coreutils}/bin/sleep 1
    done
    exec ${uniclipboardPackage}/bin/uniclipboard "$@"
  '';
  autostartEntry = pkgs.writeText "uniclipboard-autostart.desktop" ''
    [Desktop Entry]
    Name=UniClipboard
    Type=Application
    Exec=${waitForKeyring}
    Terminal=false
    X-GNOME-Autostart-enabled=true
  '';
in
{
  environment.systemPackages = [
    uniclipboardPackage
  ];

  home-manager.sharedModules = [
    (_: {
      xdg.autostart.enable = true;
      xdg.autostart.entries = [ autostartEntry ];
    })
  ];
}
