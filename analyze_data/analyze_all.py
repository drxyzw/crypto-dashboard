import sys, subprocess

subprocess.run([sys.executable, "analyze_data/calc_moment.py"])
subprocess.run([sys.executable, "analyze_data/calc_regression.py"])
