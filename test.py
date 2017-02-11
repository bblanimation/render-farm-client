import subprocess

print("running")

rub = subprocess.call("rsync --version", shell=True)
print(rub)

rub = subprocess.call("rsygc --version", shell=True)
print(rub)
