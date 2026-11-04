import time
import subprocess
import requests
import json
from pathlib import Path
from printNice import *

class Formatting:
    Bold = "\x1b[1m"
    Dim = "\x1b[2m"    
    Reset = "\x1b[0m"

class Llamacpp_server:

    def __init__(self):
        # Configuration
        self.SERVER_URL = "http://127.0.0.1:1234"
        self.CONF_PATH = Path("/var/lib/llama/server.conf")
        self.MAX_LAYERS = 32  # Qwen 3.5 9B has 32 layers total
        self.MODEL = "Qwen3.5-9B-Q4_K_M.gguf"


    def start_server(self, layers: int=32):
        """Triggers the llamacpp-serve script and dynamically polls /health until ready."""
        print(f"\n[Service] Starting llamacpp with {self.MODEL} model and {layers} GPU layers...")
        
        # Trigger the shell script
        subprocess.run(f"llamacpp-serve {self.MODEL} {layers}", shell=True, check=True)
        
        print("[Service] Model is loaded into VRAM..")
        start_time = time.time()
        
        while time.time() - start_time < 60:  # Timeout after 60 seconds
            try:
                # llama-server returns HTTP 503 while loading, and HTTP 200 {"status": "ok"} when ready
                res = requests.get(f"{self.SERVER_URL}/health", timeout=1)
                
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "ok":
                        print(f"[Service] Server started in {round(time.time() - start_time, 2)}s and is now fully loaded and ready.")
                        time.sleep(0.5)  # Micro-stabilization pause
                        return True
                elif res.status_code == 503:
                    # Model is still loading weights into VRAM; keep waiting
                    pass
            except requests.exceptions.RequestException:
                # Connection refused can happen briefly while the HTTP socket binds
                pass
                
            # Verify the background systemd service didn't crash during boot
            status_check = subprocess.run("systemctl is-active llama-custom-server", shell=True, capture_output=True, text=True)
            if "inactive" in status_check.stdout or "failed" in status_check.stdout:
                print("\n❌ [Service] llama-custom-server crashed during startup!")
                subprocess.run("journalctl -u llama-custom-server -n 10 --no-pager", shell=True)
                raise RuntimeError("Server process died unexpectedly during startup.")

            time.sleep(1)

        raise RuntimeError("Server failed to become healthy within the timeout period.")


    def _get_current_vram_usage() -> float:
        """Queries nvidia-smi for current VRAM usage on GPU 0."""
        try:
            cmd = "nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            vram_mb = result.stdout.strip()
            return float(vram_mb)
        except Exception:
            return 0


    def _streamThinking(self, message):
        thinking_chunk = message.get("reasoning_content", "")
        if thinking_chunk:
            print(Formatting.Dim + thinking_chunk, end="", flush=True)
            return thinking_chunk
        return False

    def _streamContent(self, message):
        content_chunk = message.get("content", "")
        if content_chunk:
            print(content_chunk, end="", flush=True)
            return content_chunk
        return False

        
    def stream_chat(self, prompt: str):
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Do not use internal reasoning, chain of thought, or <think> tags. Answer directly."},
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": "current-model.gguf",
            "messages": messages,
            "stream": True, 
            "temperature": 0.1,
            # "max_tokens": 150  
        }

        try:
            response = requests.post(f"{self.SERVER_URL}/v1/chat/completions", json=payload, timeout=60, stream=True)
            response.raise_for_status()

            accumulated_tool_calls = []

            doneThinking = False
            fullThinking = ""
            fullContent = ""

            # Iterate line-by-line through llama server streaming NDJSON output
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    # response comming in SSE format: data: {..JSON..}
                    if decoded_line.startswith('data: '):
                        content_str = decoded_line[6:].strip()
                    
                    # The stream ends with a '[DONE]' token
                    if content_str == '[DONE]':
                        break

                    chunk = json.loads(content_str)
                    message = chunk.get("choices")[0].get("delta")

                    # print(chunk)
                    # printNiceJSON(chunk)

                    # Stream the thinking process
                    thinkingChunk = self._streamThinking(message)
                    isThinking = thinkingChunk != False
                    if thinkingChunk:
                        fullThinking += thinkingChunk

                    if doneThinking and not isThinking:
                        print(Formatting.Reset + "\n")
                        doneThinking = False
                    if isThinking:
                        doneThinking = isThinking

                    # Stream the response contend the LLM provided to the user
                    contentChunk = self._streamContent(message)
                    if contentChunk:
                        fullContent += contentChunk

            # the last chunk received
            else:
                chunk["message"]["thinking"] = fullThinking
                chunk["message"]["content"] = fullContent

                printNiceJSON(chunk)

                return chunk

        finally:
            pass




server = Llamacpp_server()


server.start_server(32)

server.stream_chat("hello")



