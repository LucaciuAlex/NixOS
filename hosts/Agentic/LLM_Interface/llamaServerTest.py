import time
import requests
import json

class LlamaCppDiagnostics:
    def __init__(self, base_url: str = "http://127.0.0.1:1234"):
        self.base_url = base_url

    def get_props(self) -> dict:
        """Fetches server properties, active model configurations, and context settings."""
        try:
            response = requests.get(f"{self.base_url}/props", timeout=2)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Failed to connect to /props: {e}"}

    def get_slots(self) -> list:
        """Fetches slot states, token processing queues, and active inference metrics."""
        try:
            response = requests.get(f"{self.base_url}/slots", timeout=2)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return [{"error": f"Failed to connect to /slots: {e}"}]

    def display_dashboard(self):
        """Prints a unified diagnostics dashboard matching Ollama's telemetry layout."""
        print("\n" + "=" * 80)
        print(" 📊 LLAMA.CPP SERVER & SYSTEM DIAGNOSTICS DASHBOARD")
        print("=" * 80)

        print("\n[1] Server Properties & Model Configuration (/props):")
        props = self.get_props()
        if "error" in props:
            print(f"  ❌ {props['error']}")
            print("  (Make sure llama-custom-server is running via systemctl)")
        else:
            print(json.dumps(props, indent=2))

        print("\n[2] Active Slot State & Metrics (/slots):")
        slots = self.get_slots()
        if isinstance(slots, list) and len(slots) > 0 and "error" in slots[0]:
            print(f"  ❌ {slots[0]['error']}")
        else:
            print(json.dumps(slots, indent=2))
        
        print("=" * 80 + "\n")



monitor = LlamaCppDiagnostics(base_url="http://127.0.0.1:1234")

try:
    while True:
        monitor.display_dashboard()
        print("Options:")
        print("  [Enter] Refresh stats dashboard")
        print("  [q]     Quit monitor")
        choice = input("Command > ").strip().lower()
        
        if choice == 'q':
            print("[Monitor] Exiting...")
            break
except KeyboardInterrupt:
    print("\n[Monitor] Interrupted by user. Exiting.")