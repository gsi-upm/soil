#!/bin/env python
import sys
import os
import subprocess
import argparse
parser = argparse.ArgumentParser(
                    prog='Profiler for soil')
parser.add_argument('--suffix', default=None)
parser.add_argument('files', nargs="+")

args = parser.parse_args()

for fname in args.files:
    suffix = ("_" + args.suffix) if args.suffix else ""
    simname = f"{fname.replace('/', '-')}{suffix}"
    profpath = os.path.join("profs", simname + ".prof")

    print(f"Running {fname} and saving profile to {profpath}")
    subprocess.call(["python", "-m", "cProfile", "-o", profpath, fname])
