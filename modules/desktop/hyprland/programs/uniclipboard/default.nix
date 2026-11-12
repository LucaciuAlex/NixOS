{
  inputs,
  pkgs,
  ...
}:

{
  environment.systemPackage = [
    inputs.uniclipboard.packages.${pkgs.system}.default
  ];
}
