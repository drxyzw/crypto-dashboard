import sys, subprocess

subprocess.run([sys.executable, "-m", "market.create_volatility_surface"])
subprocess.run([sys.executable, "-m", "market.create_q_probability"])
