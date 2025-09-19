import sys, subprocess

subprocess.run([sys.executable, "market/create_volatility_surface.py"])
subprocess.run([sys.executable, "market/create_q_probability.py"])
