import sys, subprocess

subprocess.run([sys.executable, "-m", "fetch_data.SOFR"], check=True)
subprocess.run([sys.executable, "-m", "fetch_data.Term_SOFR"], check=True)
subprocess.run([sys.executable, "-m", "fetch_data.CME_SOFR_futures"], check=True)
subprocess.run([sys.executable, "-m", "fetch_data.CME_SOFR_OIS"], check=True)
subprocess.run([sys.executable, "-m", "fetch_data.CME_CRYPTO_RR"], check=True)
subprocess.run([sys.executable, "-m", "fetch_data.CME_CRYPTO_future"], check=True)
subprocess.run([sys.executable, "-m", "fetch_data.CME_CRYPTO_option"], check=True)
