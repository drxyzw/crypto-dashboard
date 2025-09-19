import sys, subprocess

subprocess.run([sys.executable, "process_raw_data/yield_curve.py"])
subprocess.run([sys.executable, "process_raw_data/asset_spot.py"])
subprocess.run([sys.executable, "process_raw_data/asset_futures.py"])
subprocess.run([sys.executable, "process_raw_data/asset_option.py"])
