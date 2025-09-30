import sys, subprocess

subprocess.run([sys.executable, "-m", "fetch_data.SOFR"])
subprocess.run([sys.executable, "-m", "fetch_data.Term_SOFR"])
subprocess.run([sys.executable, "-m", "fetch_data.CME_SOFR_futures"])
subprocess.run([sys.executable, "-m", "fetch_data.CME_SOFR_OIS"])
subprocess.run([sys.executable, "-m", "fetch_data.CME_CRYPTO_RR"])
subprocess.run([sys.executable, "-m", "fetch_data.CME_CRYPTO_future"])
subprocess.run([sys.executable, "-m", "fetch_data.CME_CRYPTO_option"])
