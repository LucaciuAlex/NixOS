{ config, pkgs, ... }:

let 
  # 1. Capture the localized files path relative to this Nix module 
  localManifestFile = ./models_manifest.json;
  localOrchScript = ./orchestrator.py; 
  
  # 2. Package the Python multi-agent orchestrator natively 
  nixos-agent-orch = pkgs.writers.writePython3Bin "nixos-agent-orch" { 
    libraries = with pkgs.python3Packages; [ requests ]; 
  } '' 
    import os 
    import sys 
    
    # Inject the persistent Nix store path of the manifest into the runtime environment 
    os.environ["AGENT_MANIFEST_PATH"] = "${localManifestFile}"
    
    # Execute our external python script logic 
    with open("${localOrchScript}", "r") as f: 
      exec(f.read()) 
  '';
    
  # 3. Optimized Aider wrapper for ESP32 Firmware Development 
  # This uses the specific flags ('--edit-format whole') 
  esp-chat = pkgs.writeShellScriptBin "esp-chat" '' 
    echo "⚡ Spawning dedicated firmware pairing agent (Qwen2.5-Coder:7b)..." 
    echo "⚙️ Configured for local execution (Whole-file edits to prevent syntax formatting failures)" 
    
    exec ${pkgs.aider-chat}/bin/aider \
      --model ollama/qwen2.5-coder:7b \ 
      --api-key ollama=no-key-needed \ 
      --edit-format whole \ 
      --suggest-shell-commands false \ 
      "$@" 
  '';
  
in
{
  # Allow proprietary packages for NVIDIA drivers and CUDA acceleration 
  nixpkgs.config.allowUnfree = true; 
  
  # Modern Ollama Configuration with Native CUDA Hardware Acceleration 
  services.ollama = { 
    enable = true; 
    package = pkgs.ollama-cuda; 
  };
  
  # Serial Port Access for Microcontroller compilation and flashing 
  users.users.luchylex = {
    extraGroups = [ "dialout" "tty" ]; 
  }; 
  
  # Local SearXNG Private Search Engine Configuration 
  services.searx = { 
    enable = true; 
    settings = { 
      server = { 
        port = 8888; 
        bind_address = "127.0.0.1"; 
        secret_key = "luchylex_local_key_for_orchestrator"; 
      }; 
      search.safe_search = 1; 
      engines = [ 
        { name = "bing"; engine = "bing"; shortcut = "bi"; }
        { name = "duckduckgo"; engine = "duckduckgo"; shortcut = "ddg"; } 
      ]; 
      formats = [ "html" "json" ];
    }; 
  }; 
  
  # Core System Packages & Custom CLI Utilities specific for this flake
  environment.systemPackages = with pkgs; [
    ollama-cuda
    aider-chat 
    esptool 
    platformio 
    python3Packages.pip 
    python3Packages.pyserial 
    git 
    
    # Custom Orchestrator components 
    nixos-agent-orch 
    esp-chat 
  ]; 
  
  # Global System Shell Aliases 
  environment.shellAliases = {
    # 🤖 Launches the persistent, multi-agent orchestrator loop 
    llm-chat = "nixos-agent-orch";
    
    # 🧹 Resets the active session files to clear working context 
    nixos-chat-reset = "rm -f session_log.md .session_state.json && echo 'session state cleanly reset!'";
     
    # 🔌 Quick command to launch esptool to check connected boards 
    esp-check = "esptool.py flash_id"; 
  };

}
