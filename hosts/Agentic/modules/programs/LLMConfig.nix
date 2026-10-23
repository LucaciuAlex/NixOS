{ config, pkgs, ... }:

let
  # 1. Capture the localized files path relative to this Nix module
  localManifestFile = ./models_manifest.json;
  orchestratorSystemPrompt = ./orchestratorSystemPrompt.txt;
  localOrchScript = ./orchestrator.py;
  # llamacppModel = ./l_models/Meta-Llama-3.1-8B-Instruct-Q6_K.gguf;
  # ollamaCustomParamsFIle = ./Qwen3.5CustomModelFile;

  myPythonEnv = pkgs.python3.withPackages (ps: [
    ps.requests
  ]);

  # nixos-agent-orchestrator
  nixos-agent-orchestrator = pkgs.writeShellScriptBin "nixos-agent-orchestrator" ''
    export AGENT_MANIFEST_PATH="${localManifestFile}"
    export ORCHESTRATOR_SYSTEM_PROMPT_PATH="${orchestratorSystemPrompt}"

    exec ${myPythonEnv}/bin/python3 ${localOrchScript}
  '';

  # Aider wrapper for ESP32 Firmware Development
  # This uses the specific flags ('--edit-format whole')go on
  esp-chat = pkgs.writeShellScriptBin "esp-chat" ''
    echo "Spawning dedicated firmware pairing agent"
    echo "Configured for local execution "

    exec ${pkgs.aider-chat}/bin/aider \
      --model ollama/qwen2.5-coder:7b \
      --api-key ollama=no-key-needed \
      --edit-format whole \
      --suggest-shell-commands false \
      "$@"
  '';

in
{
  # Serial Port Access for Microcontroller compilation and flashing
  users.users.luchylex = {
    extraGroups = [
      "dialout"
      "tty"
    ];
  };

  #Allow proprietary packages for NVIDIA drivers and CUDA acceleration
  nixpkgs.config.allowUnfree = true;

  # Modern Ollama Configuration with Native CUDA Hardware Acceleration
  services.ollama = {
    enable = true;
    package = pkgs.ollama-cuda;

    environmentVariables = {
      OLLAMA_NUM_PARALLEL = "1";
      OLLAMA_FLASH_ATTENTION = "1";
      OLLAMA_KV_CACHE_TYPE = "q4_0";

    };
  };

  # # provide ollama with custom parameters:
  # ollamaCustomParams = ''
  #   exec ${pkgs.ollama-cuda}/bin/ollama create customQwen3.5_9B -f ${ollamaCustomParamsFIle}
  # '';

  # services.llama-cpp = {
  #   enable = true;
  #   # Pass -1 to automatically offload ALL possible layers to your A3000 GPU
  #   model = "${llamacppModel}";
  # };

  # systemd.services.llama-custom-server = {
  #   description = "Llama.cpp Server with CUDA";
  #   after = [ "network.target" ];
  #   wantedBy = [ "multi-user.target" ];

  #   preStart = ''
  #     mkdir -p /var/lib/llama
  #     if [ ! -f /var/lib/llama/current-model.gguf ]; then
  #       touch /var/lib/llama/current-model.gguf
  #     fi
  #   '';

  #   serviceConfig = {
  #     ExecStart = ''
  #       ${pkgs.llama-cpp.override { cudaSupport = true; }}/bin/llama-server \
  #         --host 127.0.0.1 \
  #         --port 8080 \
  #         --n-gpu-layers 32 \
  #         --flash-attn on \
  #         --model /var/lib/llama/Meta-Llama-3 .1 - 8 B-Instruct-Q5_K_M.gguf
  #     '';
  #     Restart = "on-failure";
  #     RestartSec = "5s";
  #   };
  # };

  # web app for chat
  services.open-webui = {
    enable = true;
    port = 8080;
    environment = {
      OLLAMA_BASE_URL = "http://127.0.0.1:11434";
      # Oprește telemetria pentru intimitate totală locală
      ANONYMIZED_TELEMETRY = "False";
    };
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
        {
          name = "bing";
          engine = "bing";
          shortcut = "bi";
        }
        {
          name = "duckduckgo";
          engine = "duckduckgo";
          shortcut = "ddg";
        }
      ];
      formats = [
        "html"
        "json"
      ];
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
    nixos-agent-orchestrator
    esp-chat
    koboldcpp
  ];

  # Zsh System Shell Aliases
  programs.zsh = {
    enable = true;
    shellAliases = {
      # Launches the persistent, multi-agent orchestrator loop
      llm-chat = "nixos-agent-orchestrator";

      # Resets the active session files to clear working context
      nixos-chat-reset = "rm -f session_log.md .session_state.json && echo 'session state cleanly reset!'";

      # Quick command to launch esptool to check connected boards
      esp-check = "esptool.py flash_id";
    };
  };

}
