import subprocess
import threading
import time
import ollama

class OllamaDiagnosticsSandbox:
    def __init__(self, model_name: str = "qwen2.5:7b"):
        self.model_name = model_name
        self.chat_active = False

    def run_system_command(self, cmd: list) -> str:
        """Helper to run system diagnostics like nvidia-smi or journalctl."""
        try:
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"Error executing {' '.join(cmd)}: {e.stderr.strip()}"
        except FileNotFoundError:
            return f"Command not found: {cmd[0]}. (Note: journalctl/nvidia-smi require Linux/NVIDIA drivers)."

    def get_nvidia_stats(self) -> str:
        """Queries precise VRAM usage and GPU utilization."""
        return self.run_system_command([
            "nvidia-smi", 
            "--query-gpu=memory.total,memory.used,memory.free,utilization.gpu", 
            "--format=csv"
        ])

    def get_journal_logs(self) -> str:
        """Fetches recent Ollama systemd service logs."""
        return self.run_system_command(["journalctl", "-u", "ollama", "-n", "20", "--no-pager"])

    def get_ollama_ps(self):
        """Queries ollama.ps() to check loaded models and VRAM footprints."""
        try:
            return ollama.ps()
        except Exception as e:
            return {"error": str(e)}

    def background_chat_worker(self):
        """
        Keeps a model active in memory by opening a chat loop with an infinite keep_alive.
        """
        print(f"\n[Sandbox] Launching model '{self.model_name}' with keep_alive='-1' (infinite)...")
        self.chat_active = True
        
        try:
            # First touch loads the model into VRAM
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hello! System check initialized."}],
                keep_alive=-1  # Keeps the model loaded indefinitely until closed
            )
            print(f"\n[Sandbox] Model loaded successfully. Initial reply: {response['message']['content'][:60]}...")
            
            # Keep thread alive to monitor state
            while self.chat_active:
                time.sleep(2)
                
        except Exception as e:
            print(f"\n[Sandbox] Chat thread error: {e}")

    def display_dashboard(self):
        """Prints all available telemetry data in one clean layout."""
        print("\n" + "="*80)
        print(" 📊 OLLAMA & SYSTEM DIAGNOSTICS DASHBOARD")
        print("="*80)
        
        print("\n[1] ollama.ps() - Active Models & VRAM footprints:")
        ps_data = self.get_ollama_ps()
        print(ps_data)
        
        print("\n[2] nvidia-smi VRAM Distribution:")
        print(self.get_nvidia_stats())

if __name__ == "__main__":
    # Choose your active model tag here
    MODEL_TO_TEST = "customQwen3.5_RT"
    
    sandbox = OllamaDiagnosticsSandbox(model_name=MODEL_TO_TEST)
    
    # 1. Start the chat instance in a background thread to keep it alive
    chat_thread = threading.Thread(target=sandbox.background_chat_worker, daemon=True)
    chat_thread.start()
    
    # Give it a couple seconds to allocate weights into VRAM
    time.sleep(3)

    try:
        while True:
            # 2. Render all statistics dynamically
            sandbox.display_dashboard()
            
            print("Options:")
            print("  [Enter] Refresh stats dashboard")
            print("  [q]     Quit and unload model")
            choice = input("Command > ").strip().lower()
            
            if choice == 'q':
                print("[Sandbox] Shutting down session...")
                sandbox.chat_active = False
                break
                
    except KeyboardInterrupt:
        print("\n[Sandbox] Interrupted by user. Exiting.")