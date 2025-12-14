#!/usr/bin/env python3
"""
Extract stacktraces from _report.jsonl files in folders ending with
'Deployment Stacktrace Health', then archive all .txt files into a .tar.gz file.
"""

import argparse
import os
import tarfile
import json
import re
from pathlib import Path
from datetime import datetime


def extract_after_excluded_containers(obj_value_str: str) -> str | None:
    """Extract text after '**Excluded Containers:**' delimiter."""
    delim = '**Excluded Containers:**'
    idx = obj_value_str.find(delim)
    if idx == -1:
        return None
    after = obj_value_str[idx + len(delim):]
    return after.strip()


def strip_timestamp_prefix(text: str) -> str:
    """Remove timestamp prefixes from each line."""
    return '\n'.join([
        re.sub(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{9}Z\s+', '', line)
        for line in text.splitlines()
    ])


def extract_stacktrace_from_jsonl(jsonl_path: Path) -> str | None:
    """
    Extract stacktrace from the last JSON object in a .jsonl file.

    Args:
        jsonl_path: Path to the _report.jsonl file

    Returns:
        Extracted and normalized stacktrace text, or None if extraction fails
    """
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if len(lines) < 1:
            print(f"  Warning: {jsonl_path} has < 1 line, skipping")
            return None

        # Parse the last line
        rec = json.loads(lines[-1])
        obj = rec.get("obj")

        if not isinstance(obj, str):
            print(f"  Warning: 'obj' field is not a string in {jsonl_path}")
            return None

        stacktrace_section = extract_after_excluded_containers(obj)
        if stacktrace_section is None:
            print(f"  Warning: '**Excluded Containers:**' delimiter not found in {jsonl_path}")
            return None

        return strip_timestamp_prefix(stacktrace_section)

    except Exception as e:
        print(f"  Error processing {jsonl_path}: {e}")
        return None


def process_stacktrace_health_folders(root_path: Path) -> dict[str, list[Path]]:
    """
    Find folders ending with 'Deployment Stacktrace Health', extract stacktraces
    from _report.jsonl files, and collect all .txt files.

    Args:
        root_path: Root directory to search

    Returns:
        Dictionary mapping folder paths to lists of .txt files
    """
    folder_txt_files = {}

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Check if current directory name ends with "Deployment Stacktrace Health"
        if os.path.basename(dirpath).endswith("Deployment Stacktrace Health"):
            dir_path = Path(dirpath)

            # Find and process _report.jsonl files
            report_jsonl_files = [f for f in filenames if f.endswith("_report.jsonl")]

            for jsonl_file in report_jsonl_files:
                jsonl_path = dir_path / jsonl_file
                print(f"Processing: {jsonl_path}")

                stacktrace = extract_stacktrace_from_jsonl(jsonl_path)
                if stacktrace:
                    # Generate output filename: replace _report.jsonl with _stacktrace.txt
                    output_filename = jsonl_file.replace('_report.jsonl', '_stacktrace.txt')
                    output_path = dir_path / output_filename

                    # Write stacktrace to file
                    with open(output_path, 'w', encoding='utf-8') as fout:
                        fout.write(stacktrace)
                    print(f"  Created: {output_filename}")

            # Collect all .txt files in this folder (including newly created ones)
            txt_files = [
                dir_path / f
                for f in os.listdir(dir_path)
                if f.endswith(".txt")
            ]

            if txt_files:
                folder_txt_files[dirpath] = txt_files

    return folder_txt_files


def create_archive(folder_txt_files: dict[str, list[Path]],
                   output_prefix: str,
                   root_path: Path) -> str:
    """
    Create a .tar.gz archive containing all found .txt files.

    Args:
        folder_txt_files: Dictionary mapping folder paths to .txt files
        output_prefix: Prefix for the output archive filename
        root_path: Root path for calculating relative paths

    Returns:
        Path to created archive
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"{output_prefix}_{timestamp}.tar.gz"

    with tarfile.open(archive_name, "w:gz") as tar:
        for folder_path, txt_files in folder_txt_files.items():
            for txt_file in txt_files:
                # Calculate relative path from root to maintain folder structure
                try:
                    arcname = txt_file.relative_to(root_path)
                except ValueError:
                    # If relative_to fails, use the full path
                    arcname = txt_file

                tar.add(txt_file, arcname=str(arcname))
                print(f"Added: {arcname}")

    return archive_name


def main():
    parser = argparse.ArgumentParser(
        description="Archive .txt files from 'Deployment Stacktrace Health' folders"
    )
    parser.add_argument(
        "root_path",
        type=str,
        help="Root directory to search for folders"
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="stacktrace_health_stacktraces",
        help="Prefix for output .tar.gz filename (default: stacktrace_health)"
    )

    args = parser.parse_args()

    root_path = Path(args.root_path)

    if not root_path.exists():
        print(f"Error: Path '{root_path}' does not exist")
        return 1

    if not root_path.is_dir():
        print(f"Error: Path '{root_path}' is not a directory")
        return 1

    print(f"Searching for folders ending with 'Deployment Stacktrace Health'...")
    print(f"Root path: {root_path}")
    print()

    folder_txt_files = process_stacktrace_health_folders(root_path)

    if not folder_txt_files:
        print("No .txt files found in matching folders")
        return 0

    total_files = sum(len(files) for files in folder_txt_files.values())
    print(f"Found {total_files} .txt files in {len(folder_txt_files)} folders")
    print()

    print("Creating archive...")
    archive_name = create_archive(folder_txt_files, args.prefix, root_path)

    print()
    print(f"Successfully created archive: {archive_name}")
    print(f"Total files archived: {total_files}")

    return 0


if __name__ == "__main__":
    exit(main())
