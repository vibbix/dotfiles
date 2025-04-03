# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "tqdm",
# ]
# ///
import os
import sys
import subprocess
from tqdm import tqdm

def find_files(directory) -> iter:
    for root, _, files in os.walk(directory):
        for file in files:
            if 'node_modules' in root or '.git' in root:
                continue
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'rb') as f:
                    if b'\0' in f.read():
                        continue
            except:
                continue
            yield file_path

def main(directory):
    files = list(find_files(directory))
    for file in tqdm(files, desc="Processing files"):
        try:
            subprocess.check_output(['git', 'ls-files', '--error-unmatch', file], stderr=subprocess.STDOUT)
            blame_output = subprocess.check_output(['git', 'blame', '--date=format:%Y%m%d', '-f', file])
            blame_lines = blame_output.decode('utf-8').splitlines()
            for line in blame_lines:
                if '20' in line:
                    print(line)
        except subprocess.CalledProcessError:
            continue

if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    main(directory)
