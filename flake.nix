{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs =
    {
      self,
      nixpkgs,
    }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      python = (pkgs.python314.withPackages (ps: with ps; [
        colorama
        cryptography
      ]));
      
      nativeBuildInputs = with pkgs; [
        meson
        ninja
      ];

      buildInputs = with pkgs; [
        python
        hatch
      ];
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        inherit nativeBuildInputs buildInputs;
        packages = with pkgs; [
          ruff
          hactool
          ghex
        ];
      };

      packages.${system}.default = pkgs.stdenv.mkDerivation {
        name = "svgtheme";
        version = "0.1.0";
        src = ./.;


        inherit nativeBuildInputs buildInputs;
      };
    };
}
