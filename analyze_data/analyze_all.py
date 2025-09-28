import sys, subprocess

subprocess.run([sys.executable, "-m", "analyze_data.calc_moment"])
subprocess.run([sys.executable, "-m", "analyze_data.calc_regression"])
