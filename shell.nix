{ pkgs ? import <nixpkgs> { } }:
with pkgs;
mkShell {
    buildInputs = [
        (python311.withPackages (pythonPkgs: with pythonPkgs; [
            discordpy
            ollama
            python-dotenv
            pyvips
            wikipedia
            # duckduckgo-search
        ]))
    ];
    
    # Workaround: make vscode's python extension read the .venv
    shellHook = ''
        venv="$(cd $(dirname $(which python)); cd ..; pwd)"
        ln -Tsf "$venv" .venv
    '';
}
