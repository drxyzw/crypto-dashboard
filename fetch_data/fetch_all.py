import sys, subprocess

# subprocess.run([sys.executable, "-m", "fetch_data.SOFR"], text=True, stdout=sys.stdout, stderr=sys.stderr)
# subprocess.run([sys.executable, "-m", "fetch_data.Term_SOFR"], text=True, stdout=sys.stdout, stderr=sys.stderr)
subprocess.run([sys.executable, "-u", "-m", "fetch_data.CME_SOFR_futures"], text=True, stdout=sys.stdout, stderr=sys.stderr)
# subprocess.run([sys.executable, "-m", "fetch_data.CME_SOFR_OIS"], text=True, stdout=sys.stdout, stderr=sys.stderr)
# subprocess.run([sys.executable, "-m", "fetch_data.CME_CRYPTO_RR"], text=True, stdout=sys.stdout, stderr=sys.stderr)
# subprocess.run([sys.executable, "-m", "fetch_data.CME_CRYPTO_future"], text=True, stdout=sys.stdout, stderr=sys.stderr)
# subprocess.run([sys.executable, "-m", "fetch_data.CME_CRYPTO_option"], text=True, stdout=sys.stdout, stderr=sys.stderr)
