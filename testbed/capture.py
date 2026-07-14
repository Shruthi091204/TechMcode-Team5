# testbed/capture.py
import subprocess
import sys
import time

def get_docker_bridge_interface():
    """Finds the actual Linux bridge interface name for the rca_net docker network."""
    try:
        # Docker networks are usually named br-<first 12 chars of network ID>
        result = subprocess.run(
            ["docker", "network", "inspect", "rca_net", "-f", "{{.Id}}"], 
            capture_output=True, text=True, check=True
        )
        network_id = result.stdout.strip()[:12]
        return f"br-{network_id}"
    except subprocess.CalledProcessError:
        print("Error: Could not find docker network 'rca_net'. Is the testbed running?")
        sys.exit(1)

def start_capture(interface, output_file="flows.csv"):
    """Starts a tshark process capturing flow-level metrics to a CSV."""
    print(f"Starting tshark on interface {interface}...")
    
    # We capture timestamps, IP pairs, Port pairs, and frame length. 
    # P2's flow_to_kpi.py will use this to calculate latency, throughput, etc.
    cmd = [
        "tshark", "-i", interface,
        "-T", "fields",
        "-e", "frame.time_epoch", "-e", "ip.src", "-e", "ip.dst",
        "-e", "tcp.srcport", "-e", "tcp.dstport", "-e", "frame.len",
        "-E", "header=y", "-E", "separator=,"
    ]
    
    with open(output_file, "w") as f:
        # Run tshark in the background
        process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.DEVNULL)
    
    return process

if __name__ == "__main__":
    interface = get_docker_bridge_interface()
    proc = start_capture(interface)
    try:
        print(f"Capturing packets to flows.csv. Press Ctrl+C to stop.")
        # Keep main thread alive while tshark runs in background
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping capture...")
        proc.terminate()