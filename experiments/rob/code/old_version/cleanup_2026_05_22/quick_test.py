#!/usr/bin/env python3
"""
Quick test script to validate optimizations on a small subset.

This script:
1. Runs baseline version on first 20 studies
2. Runs optimized version on the same 20 studies
3. Compares results immediately

Usage:
    python quick_test.py
"""

import asyncio
import subprocess
import sys
from pathlib import Path


async def run_command(cmd: list[str], description: str) -> int:
    """Run a command and stream output."""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(cmd)}\n")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    while True:
        line = await process.stdout.readline()
        if not line:
            break
        try:
            # Try UTF-8 first
            decoded = line.decode('utf-8').rstrip()
        except UnicodeDecodeError:
            try:
                # Fallback to GBK for Windows Chinese
                decoded = line.decode('gbk').rstrip()
            except UnicodeDecodeError:
                # Last resort: ignore errors
                decoded = line.decode('utf-8', errors='ignore').rstrip()
        print(decoded)

    await process.wait()
    return process.returncode


async def main():
    """Run quick test."""

    # Check if dataset exists
    dataset_dir = Path("rob_cleaned_dataset")
    if not dataset_dir.exists():
        print(f"ERROR: Dataset directory not found: {dataset_dir}")
        print("Please ensure rob_cleaned_dataset exists in the current directory.")
        return 1

    num_files = len(list(dataset_dir.glob("*.json")))
    print(f"Found {num_files} studies in {dataset_dir}")

    if num_files == 0:
        print("ERROR: No JSON files found in dataset directory")
        return 1

    test_size = min(20, num_files)
    print(f"\nRunning quick test on first {test_size} studies...")

    # Step 1: Run baseline
    ret = await run_command(
        [
            sys.executable,
            "run_experiment.py",
            "--max_studies", str(test_size),
            "--output_dir", "results/predictions_test_baseline",
            "--concurrency", "3",
        ],
        f"STEP 1/3: Running BASELINE version ({test_size} studies)"
    )

    if ret != 0:
        print(f"\n❌ Baseline run failed with exit code {ret}")
        return ret

    # Step 2: Run optimized
    ret = await run_command(
        [
            sys.executable,
            "run_experiment_optimized.py",
            "--max_studies", str(test_size),
            "--output_dir", "results/predictions_test_optimized",
            "--concurrency", "3",
        ],
        f"STEP 2/3: Running OPTIMIZED version ({test_size} studies)"
    )

    if ret != 0:
        print(f"\n❌ Optimized run failed with exit code {ret}")
        return ret

    # Step 3: Compare results
    ret = await run_command(
        [
            sys.executable,
            "compare_results.py",
            "--baseline", "results/predictions_test_baseline",
            "--optimized", "results/predictions_test_optimized",
        ],
        "STEP 3/3: Comparing results"
    )

    if ret != 0:
        print(f"\n❌ Comparison failed with exit code {ret}")
        return ret

    print("\n" + "="*80)
    print("✅ Quick test completed successfully!")
    print("="*80)
    print("\nNext steps:")
    print("  1. Review the comparison results above")
    print("  2. If optimized version shows improvement, run full evaluation:")
    print("     python run_experiment_optimized.py")
    print("  3. Compare full results:")
    print("     python compare_results.py")
    print()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
