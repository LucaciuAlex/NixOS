{ config, pkgs, ... }:

let
  localManifestFile = ./models_manifest.json;
  orchestratorSystemPrompt = ./orchestratorSystemPrompt.txt;
  localOrchScript = ./orchestrator.py;

  myPythonEnv = pkgs.python3.withPackages (ps: [
    ps.requests
  ]);

  # Dedicated helper script: llamacpp-serve
  # Usage:
  #   llamacpp-serve <filename_or_url> [gpu_layers]
  # Examples:
  #   llamacpp-serve Meta-Llama-3.1-8B-Instruct-Q6_K.gguf 33
  #   llamacpp-serve https://huggingface.co/.../model.gguf 32

  llamacpp-serve = pkgs.writeShellScriptBin "llamacpp-serve" ''
    set -e
    MODELS_DIR="/home/luchylex/models"
    VAR_DIR="/var/lib/llama"

    sudo mkdir -p "$MODELS_DIR"
    sudo mkdir -p "$VAR_DIR"

    INPUT="$1"
    GPU_LAYERS="''${2:-32}" # Default to 32 layers if not specified

    if [ -z "$INPUT" ]; then
      echo "Error: No model name or URL provided."
      echo "Usage: llamacpp-serve <model_filename_or_url> [gpu_layers]"
      echo ""
      echo "Available models in $MODELS_DIR:"
      if [ -d "$MODELS_DIR" ]; then
        ls -lh "$MODELS_DIR" | grep '\.gguf$' || echo "  (none found)"
      else
        echo "  (directory does not exist yet)"
      fi
      exit 1
    fi

    TARGET_MODEL=""

    # Check if input is a URL (download if not cached)
    if [[ "$INPUT" =~ ^https?:// ]]; then
      FILENAME=$(basename "$INPUT" | cut -d? -f1)
      TARGET_MODEL="$MODELS_DIR/$FILENAME"

      if [ -f "$TARGET_MODEL" ]; then
        echo "Model '$FILENAME' already exists locally in $MODELS_DIR. Skipping download."
      else
        echo "Downloading '$FILENAME' from Hugging Face..."
        sudo curl -L -C - "$INPUT" -o "$TARGET_MODEL.tmp"
        sudo mv "$TARGET_MODEL.tmp" "$TARGET_MODEL"
      fi
    else
      # Treat input as a local filename inside MODELS_DIR or an absolute path
      if [ -f "$MODELS_DIR/$INPUT" ]; then
        TARGET_MODEL="$MODELS_DIR/$INPUT"
      elif [ -f "$INPUT" ]; then
        TARGET_MODEL="$INPUT"
      else
        echo "Error: Model file '$INPUT' not found locally in $MODELS_DIR."
        exit 1
      fi
    fi

    echo "Setting active model symlink to: $TARGET_MODEL"
    sudo ln -sf "$TARGET_MODEL" "$VAR_DIR/current-model.gguf"

    # Persist runtime settings so the systemd service picks them up
    echo "GPU_LAYERS=$GPU_LAYERS" | sudo tee "$VAR_DIR/server.conf" > /dev/null

    echo "Restarting llama-custom-server with new model and settings..."
    sudo systemctl restart llama-custom-server
    echo "Success! llama-server is now running $FILENAME."
  '';

  llamacpp-stop = pkgs.writeShellScriptBin "llamacpp-stop" ''
    sudo systemctl stop llama-custom-server
  '';

  # Wrapper runner script for systemd to parse runtime settings dynamically
  llamaServerRunner = pkgs.writeShellScript "llama-server-runner" ''
    if [ -f /var/lib/llama/server.conf ]; then
      source /var/lib/llama/server.conf
    fi

    GPU_LAYERS="''${GPU_LAYERS:-32}"

    exec ${pkgs.llama-cpp.override { cudaSupport = true; }}/bin/llama-server \
      --host 127.0.0.1 \
      --port 1234 \
      --model /var/lib/llama/current-model.gguf \
      --n-gpu-layers "$GPU_LAYERS" \
      --flash-attn on \
      --ctx-size 8192 \
      --parallel 1 \
      --cache-type-k q8_0 \
      --cache-type-v q8_0 \
      --reasoning-format deepseek
  '';

  nixos-agent-orchestrator = pkgs.writeShellScriptBin "nixos-agent-orchestrator" ''
    export AGENT_MANIFEST_PATH="${localManifestFile}"
    export ORCHESTRATOR_SYSTEM_PROMPT_PATH="${orchestratorSystemPrompt}"
    exec ${myPythonEnv}/bin/python3 ${localOrchScript}
  '';

  esp-chat = pkgs.writeShellScriptBin "esp-chat" ''
    echo "Spawning dedicated firmware pairing agent"
    exec ${pkgs.aider-chat}/bin/aider \
      --model ollama/qwen2.5-coder:7b \
      --api-key ollama=no-key-needed \
      --edit-format whole \
      --suggest-shell-commands false \
      "$@"
  '';

in
{
  users.users.luchylex = {
    extraGroups = [
      "dialout"
      "tty"
    ];
  };

  nixpkgs.config.allowUnfree = true;

  services.ollama = {
    enable = true;
    package = pkgs.ollama-cuda;
    environmentVariables = {
      OLLAMA_NUM_PARALLEL = "1";
      OLLAMA_FLASH_ATTENTION = "1";
      OLLAMA_KV_CACHE_TYPE = "q8_0";
    };
  };

  # Systemd Service pointing to the dynamic runner wrapper
  systemd.services.llama-custom-server = {
    description = "Llama.cpp Server with CUDA";
    after = [ "network.target" ];
    wantedBy = [ "multi-user.target" ];

    preStart = ''
      mkdir -p /var/lib/llama
      if [ ! -f /var/lib/llama/current-model.gguf ]; then
        touch /var/lib/llama/current-model.gguf
      fi
      if [ ! -f /var/lib/llama/server.conf ]; then
        echo "GPU_LAYERS=32" > /var/lib/llama/server.conf
      fi
    '';

    serviceConfig = {
      ExecStart = "${llamaServerRunner}";
      Restart = "on-failure";
      RestartSec = "5s";
    };
  };

  ##########################################################

  services.open-webui = {
    enable = true;
    port = 8080;
    environment = {
      OLLAMA_BASE_URL = "http://127.0.0.1:11434";
      ANONYMIZED_TELEMETRY = "False";
    };
  };

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

  environment.systemPackages = with pkgs; [
    ollama-cuda
    aider-chat
    esptool
    platformio
    python3Packages.pip
    python3Packages.pyserial
    git
    nixos-agent-orchestrator
    esp-chat
    koboldcpp
    llamacpp-serve
    llamacpp-stop
  ];

  programs.zsh = {
    enable = true;
    shellAliases = {
      llm-chat = "nixos-agent-orchestrator";
      nixos-chat-reset = "rm -f session_log.md .session_state.json && echo 'session state cleanly reset!'";
      esp-check = "esptool.py flash_id";
    };
  };
}
