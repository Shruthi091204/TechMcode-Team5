# testbed/inject.py
import json
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path


def execute_scenario(scenario_path: Path) -> bool:
    """Runs the bash scenario script."""
    result = subprocess.run(["sh", str(scenario_path)], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Scenario failed: {result.stderr}")
        return False
    print(result.stdout)
    return True

def stamp_ground_truth(scenario_name: str, target_component: str, fault_type: str) -> None:
    """Writes the exact injection timestamp to ground_truth.json."""
    injection_time = datetime.now(UTC).isoformat()
    
    ground_truth = {
        "incident_id": f"inc-{uuid.uuid4().hex[:8]}",
        "scenario": scenario_name,
        "injection_timestamp": injection_time,
        "true_root_cause": {
            "component_id": target_component,
            "fault_type": fault_type
        }
    }

    # Assuming we write to the local directory, recorder.py will later move this to contracts/
    output_file = Path("ground_truth.json")
    with open(output_file, "w") as f:
        json.dump(ground_truth, f, indent=2)
    
    print(f"Ground truth stamped at {injection_time} to {output_file.name}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python inject.py <scenario_name>")
        print("Example: python inject.py link_degradation")
        sys.exit(1)

    scenario_name = sys.argv[1]
    scenario_file = Path(f"scenarios/{scenario_name}.sh")

    if not scenario_file.exists():
        print(f"Error: Scenario {scenario_file} not found.")
        sys.exit(1)

    # Hardcoding the mapping for the MVP script; can be pulled from the .sh file later
    component_mapping = {
        "link_degradation": ("db-01", "network_delay_loss"),
        "bad_config_push": ("web-01", "config_misconfiguration"),
        "nic_failure": ("app-01", "interface_down"),
        "capacity_exhaustion": ("db-01", "resource_starvation"),
        "ddos_flood": ("lb-01", "traffic_spike"),
        "port_scan": ("lb-01", "security_scan")
    }

    target_comp, fault_type = component_mapping.get(scenario_name, ("unknown", "unknown"))

    print(f"--- Starting fault injection: {scenario_name} ---")
    if execute_scenario(scenario_file):
        stamp_ground_truth(scenario_name, target_comp, fault_type)

if __name__ == "__main__":
    main()