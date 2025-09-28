import sys, subprocess

subprocess.run([sys.executable, "-m", "process_raw_data.yield_curve"])
subprocess.run([sys.executable, "-m", "process_raw_data.asset_spot"])
subprocess.run([sys.executable, "-m", "process_raw_data.asset_futures"])
subprocess.run([sys.executable, "-m", "process_raw_data.asset_option"])
