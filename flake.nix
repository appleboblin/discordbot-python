{
    inputs = {
        nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
        devenv.url = "github:cachix/devenv";
    };

    outputs =
        inputs@{ flake-parts, nixpkgs, ... }:
        flake-parts.lib.mkFlake { inherit inputs; } {
            imports = [ inputs.devenv.flakeModule ];
            systems = nixpkgs.lib.systems.flakeExposed;

            perSystem =
            { config, self', inputs', pkgs, system, ...}:
                {
                # template from iynaix
                # Per-system attributes can be defined here. The self' and inputs'
                # module parameters provide easy access to attributes of the same
                # system.
                devenv.shells.default = {
                    # https://devenv.sh/reference/options/
                    packages = with pkgs.python3Packages; [ 
                        flake8
                        black
                        requests
                        tkinter
                        numpy
                        matplotlib
                        scipy
                        opencv4
                        imutils
                        pyvips
                        discordpy
                        ollama
                        aiofiles
                        aiohttp
                        python-dotenv
                        requests
                        proxmoxer
                        paramiko
                    ];
                    dotenv.disableHint = true;
                    languages.python = {
                        enable = true;
                        venv.enable = true;
                    };
                };
                };
    };
}