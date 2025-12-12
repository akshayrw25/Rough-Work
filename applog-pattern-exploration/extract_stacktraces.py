#!/usr/bin/env python3
"""
Extract stacktraces from the 'obj' value of the 2nd JSON object in a .jsonl file,
fetching the text after '**Excluded Containers:**', and normalizing by removing any timestamp prefixes.
Saves the result to a file `{prefix}_stacktrace.txt` in the same directory as the input JSONL file.

Usage:
    python extract_stacktraces.py someprefix_someid_report.jsonl
"""
import os
import argparse
import json
import re
from pathlib import Path

def extract_after_excluded_containers(obj_value_str):
    delim = '**Excluded Containers:**'
    idx = obj_value_str.find(delim)
    if idx == -1:
        return None
    after = obj_value_str[idx + len(delim):]
    return after.strip()

def strip_timestamp_prefix(text):
    return '\n'.join([
        re.sub(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{9}Z\s+', '', line)
        for line in text.splitlines()
    ])

def extract_stacktrace_from_jsonl(jsonl_path):
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    if len(lines) < 1:
        print("File has < 1 line: cannot extract stacktrace.")
        return None
    obj = None
    try:
        rec = json.loads(lines[-1])
        obj = rec["obj"]
    except Exception as e:
        print(f"Error parsing JSON on last line: {e}")
        return None
    if not isinstance(obj, str):
        print("The 'obj' field in the last JSON object is not a string, can't extract stacktrace.")
        return None
    stacktrace_section = extract_after_excluded_containers(obj)
    if stacktrace_section is None:
        print("'**Excluded Containers:**' delimiter not found in 'obj'.")
        return None
    return strip_timestamp_prefix(stacktrace_section)

def get_prefix(jsonl_path: Path) -> str:
    basename = jsonl_path.name
    prefix = basename.split('_')[0]
    return prefix

def main():
    parser = argparse.ArgumentParser(description="Extract stacktrace after '**Excluded Containers:**' from JSONL and save as raw text file.")
    parser.add_argument('jsonl_path', type=Path, help='Path to input JSONL file')
    args = parser.parse_args()

    if not args.jsonl_path.is_file():
        print(f"File not found: {args.jsonl_path}")
        return

    stacktrace = extract_stacktrace_from_jsonl(str(args.jsonl_path))
    if stacktrace:
        file_name = os.path.basename(args.jsonl_path)
        new_file_name = file_name.replace('_report.jsonl', '_stacktrace.txt')
        output_file = args.jsonl_path.parent / new_file_name
        with open(output_file, 'w', encoding='utf-8') as fout:
            fout.write(stacktrace)
        print(f"Stacktrace written to: {output_file}")
    else:
        print("No stacktrace extracted.")

if __name__ == "__main__":
    main()
