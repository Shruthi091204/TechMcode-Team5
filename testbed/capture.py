#!/usr/bin/env python3
import subprocess
import sys

OUTPUT_FILE = "flows.csv"

def start_capture():
    print("--- Starting Packet Capture (Listening on ALL interfaces) ---")
    print(f"Saving data to {OUTPUT_FILE}... Press Ctrl+C to stop.")

    # The crucial fix: '-i', 'any' forces tshark to listen to the isolated Docker bridge
    cmd = [
        'tshark',
        '-i', 'any',           
        '-T', 'fields',
        '-E', 'header=y',
        '-E', 'separator=,',
        '-E', 'quote=d',
        '-e', 'frame.time_epoch',
        '-e', 'ip.src',
        '-e', 'ip.dst',
        '-e', 'tcp.srcport',
        '-e', 'tcp.dstport',
        '-e', 'frame.len',
        '-e', 'tcp.flags'
    ]

    try:
        # Pipe the tshark output directly into our CSV file
        with open(OUTPUT_FILE, "w") as outfile:
            process = subprocess.Popen(cmd, stdout=outfile, stderr=subprocess.DEVNULL)
            process.wait()
            
    except KeyboardInterrupt:
        print("\n--- Capture stopped by user. ---")
        process.terminate()
        process.wait()
        print(f"Network data successfully secured in {OUTPUT_FILE}")
        
    except FileNotFoundError:
        print("\nERROR: 'tshark' is not installed or not in your PATH.")
        print("Run: sudo apt-get install tshark")
        sys.exit(1)
        
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    start_capture()