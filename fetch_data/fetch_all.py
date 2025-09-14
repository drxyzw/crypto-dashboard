import sys, subprocess

subprocess.run([sys.executable, "fetch_data/SOFR.py"])
subprocess.run([sys.executable, "fetch_data/Term_SOFR.py"])
subprocess.run([sys.executable, "fetch_data/CME_SOFR_futures.py"])
subprocess.run([sys.executable, "fetch_data/CME_SOFR_OIS.py"])
subprocess.run([sys.executable, "fetch_data/CME_CRYPTO_RR.py"])
subprocess.run([sys.executable, "fetch_data/CME_CRYPTO_future.py"])
subprocess.run([sys.executable, "fetch_data/CME_CRYPTO_option.py"])
