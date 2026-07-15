# testbed/recorder.py
import csv
import subprocess
import time
from datetime import UTC, datetime

# Only tracking the active components in our physical testbed
TARGET_COMPONENTS = ["lb-01", "web-01", "app-01", "db-01"]

def poll_docker_stats(output_file="hardware_telemetry.csv", duration_seconds=60, poll_interval=2):
    """Polls CPU and Memory metrics from running docker containers."""
    print(f"Polling docker stats for {duration_seconds} seconds...")
    
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "component_id", "cpu_pct", "mem_pct"])
        
        end_time = time.time() + duration_seconds
        while time.time() < end_time:
            now = datetime.now(UTC).isoformat()
            
            # Use docker stats formatting to get exactly what we need
            cmd = ["docker", "stats", "--no-stream", "--format", "{{.Name}},{{.CPUPerc}},{{.MemPerc}}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                
                try:
                    name, cpu_str, mem_str = line.split(",")
                    
                    if name in TARGET_COMPONENTS:
                        # Strip the '%' sign and convert to float for the JSON/CSV contracts
                        cpu_pct = float(cpu_str.replace('%', ''))
                        mem_pct = float(mem_str.replace('%', ''))
                        
                        writer.writerow([now, name, cpu_pct, mem_pct])
                except ValueError:
                    # Skips header row or unexpected formats
                    continue
            
            # Wait before next poll
            time.sleep(poll_interval)
            
    print(f"Finished polling. Hardware metrics written to {output_file}")

if __name__ == "__main__":
    # In a full incident run, you would start this right before calling inject.py
    poll_docker_stats()