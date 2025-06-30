import ssl
import certifi
import os
import sys

print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Current certifi path: {certifi.where()}")
print(f"SSL cert file: {ssl.get_default_verify_paths().cafile}")

# Install certificates
import subprocess
subprocess.call(["/usr/bin/security", "find-certificate", "-a", "-p", "/System/Library/Keychains/SystemRootCertificates.keychain"], stdout=open(certifi.where(), "ab"))
subprocess.call(["/usr/bin/security", "find-certificate", "-a", "-p", "/Library/Keychains/System.keychain"], stdout=open(certifi.where(), "ab"))

print("Certificates installed successfully!")
