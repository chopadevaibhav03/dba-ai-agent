"""
Test helper: generate artificial CPU / memory load so you can watch the
agent detect it, analyze it, and recommend a fix -- without waiting for
real load to happen.

Requires stress-ng for the best results (RHEL: `sudo dnf install epel-release && sudo dnf install stress-ng`).
Falls back to a pure-Python CPU burner if stress-ng isn't installed.

Usage:
    python3 stress_test.py cpu --seconds 60
    python3 stress_test.py mem --seconds 60 --mb 1024
"""

import argparse
import multiprocessing
import shutil
import subprocess
import time


def burn_cpu(seconds: int):
    end = time.time() + seconds
    while time.time() < end:
        pass  # busy loop


def run_cpu_stress(seconds: int):
    if shutil.which("stress-ng"):
        print(f"Running stress-ng --cpu 0 --timeout {seconds}s ...")
        subprocess.run(["stress-ng", "--cpu", "0", "--timeout", f"{seconds}s"])
    else:
        print("stress-ng not found, falling back to a Python CPU burner across all cores.")
        procs = [
            multiprocessing.Process(target=burn_cpu, args=(seconds,))
            for _ in range(multiprocessing.cpu_count())
        ]
        for p in procs:
            p.start()
        for p in procs:
            p.join()


def run_mem_stress(seconds: int, mb: int):
    if shutil.which("stress-ng"):
        print(f"Running stress-ng --vm 1 --vm-bytes {mb}M --timeout {seconds}s ...")
        subprocess.run(
            ["stress-ng", "--vm", "1", "--vm-bytes", f"{mb}M", "--timeout", f"{seconds}s"]
        )
    else:
        print(f"stress-ng not found, allocating ~{mb}MB in Python for {seconds}s.")
        block = bytearray(mb * 1024 * 1024)
        for i in range(0, len(block), 4096):
            block[i] = 1  # touch pages so they're actually resident
        time.sleep(seconds)
        del block


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate test load for the OS monitoring agent")
    parser.add_argument("mode", choices=["cpu", "mem"])
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--mb", type=int, default=1024, help="MB to allocate (mem mode only)")
    args = parser.parse_args()

    if args.mode == "cpu":
        run_cpu_stress(args.seconds)
    else:
        run_mem_stress(args.seconds, args.mb)

    print("Stress test finished.")
