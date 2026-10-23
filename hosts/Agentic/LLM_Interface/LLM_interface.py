
#!/usr/bin/env python3
"""
Local AI Agent Gateway - Runs locally with Ollama + Obsidian Memory.
- Supports custom model names from your local instance  
- Uses environment variables for parameters (temperature, num_predict, etc.)  
- Logs interactions to an optional memory file in your Obsidian vault  
"""

import json, os, requests, argparse, sys, datetime
from pathlib import Path


# ========================= Configuration ========================= # 
OLLAMA_URL = "http://localhost:11434/api/generate"   # Ollama server endpoint
DEFAULT_MODEL = os.getenv("LOCAL_GPT_MODEL", "Qwen3.5:9B")  # Override with your model name  
PARAMS = {
    "temperature": float(os.getenv("OLLAMA_TEMP", "0.6")),
    "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "2048")),
    "stop": os.getenv("OLLAMA_STOP_TOKENS", "").split(",") if os.getenv("OLLAMA_STOP_TOKENS", "") else []
}

ALLOWED_ROOT = Path("/home/myUser/Documents").expanduser()  # Adjust to your Documents path  
OBSIDIAN_MEMORY_DIR = ALLOWED_ROOT / "A.I.Brain"   # Obsidian vault memory folder


def query_ollama(system_prompt: str, messages: list):
    """Send prompt to Ollama with configured parameters"""

    print("inside querry function")
    
    payload_messages = [{"role": role, "content": content} for role, content in messages]

    print(f"payload message: {payload_messages}")

    try:
        r = requests.post(OLLAMA_URL, json={
            "model": DEFAULT_MODEL,
            "messages": payload_messages,
            "stream": False,
            **PARAMS  # temperature, num_predict go here if supported by model
        }, timeout=60)

        if not r.ok:
            print(f"❌ Ollama error {r.status_code}: {r.text[:200]}")
            return None
            
    except Exception as e:
        print(f"\n⚠️  Error contacting local service: {e}")
        return None
    
    try:
        response = r.json()
        
        # Handle different possible JSON structures from Ollama  
        content = (response.get("response", "") or 
                    (response.get('message', {}).get('content', "")) if isinstance(response, dict) else str(r.text[:2048]))

        return content.strip()
    except Exception:
        print(f"⚠️  Could not parse Ollama response")
        return None


def get_file_tree(root_dir: Path = ALLOWED_ROOT):
    """Return file listing WITHOUT exposing full contents (security sandbox)"""
    
    try:
        files = []

        def walk_paths(current_path, depth=0):
            if current_path.is_dir():
                for item in sorted(current_path.iterdir()):
                    entry_type = "[DIR]" if item.is_dir() else f"[FILE {item.name}]"
                    rel_path = str(item.relative_to(root_dir))

                    # Limit recursion to avoid context bloat  
                    files.append(f"{entry_type} 📁/📄 | Path: /{rel_path}")

            elif current_path.is_file():
                entry_type = "[FILE" if len(current_path.name) < 10 else " [F]" 
                rel_path = str(current_path.relative_to(root_dir))

                # Only show file type/extension, not content
                files.append(f"{entry_type} {current_path.suffix or 'TXT'} | Path: /{rel_path}")

        walk_paths(Path("."), 0)

    except Exception as e:
        print(f"⚠️  File tree error (permissions?): {e}")
    
    return "\n".join(files[:50]) if files else "No accessible files found."


def log_to_obsidian_memory(prompt, response):
    """Write interaction to Obsidian vault memory file"""
    
    log_path = OBSIDIAN_MEMORY_DIR / "memory_logs.txt"

    try: 
        with open(log_path, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if not (OBSIDIAN_MEMORY_DIR.exists() and OBSIDIAN_MEMORY_DIR.is_dir()):
                log_path.parent.mkdir(parents=True, exist_ok=True)

            content = prompt + "\n" + ("\n".join([f"{line}" for line in response.split("\n")[:10]])) if response else ""
            
            f.write(f"[{timestamp}] Query: {prompt}\nResponse:\n{content}\n\n---\n")

    except Exception as e:
        print(f"\n⚠️  Could not write to Obsidian memory log: {e}")


def main():
    parser = argparse.ArgumentParser(description="AI Agent Gateway for Ollama + Obsidian")
    parser.add_argument("prompt", help="Your command/question to send to the model")
    
    args = parser.parse_args()

    system_prompt = f"""You are a helpful local AI assistant running on NixOS. 
- You have access to files in: {ALLOWED_ROOT} (and subfolders) via file listing ONLY — never full contents unless explicitly requested through 
tools.
- Use Obsidian vault at: {OBSIDIAN_MEMORY_DIR}/memory_logs.txt for long-term memory storage  
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": args.prompt}
    ]

    print(f"📁 Current Working Dir: {Path.cwd()}")
    
    # Optional: Show file tree first if user asks about files  
    if any(word in args.prompt.lower() for word in ["file:", "cat ", "/doc/"]): 
        print("\n--- Accessible Files (No Content Exposed) ---\n")
        print(get_file_tree(ALLOWED_ROOT))

    print(f"system prompt:{system_prompt} \n message: {messages}")

    response = query_ollama(system_prompt, messages)

    print(response)
    
    if response:
        print(f"\n💬 Model Response:\n{response}")
        
        # Log interaction to Obsidian vault (example path - adjust as needed)  
        log_to_obsidian_memory(args.prompt, response[:500])

    else:  
        print("\n❌ Model returned no response. Check Ollama service.")



main() 
