"""
Java Stacktrace Comparison Tool

This module compares Java stacktraces by extracting frames, grouping them by class prefixes,
and computing similarity using Longest Common Subsequence (LCS).

EXECUTION MODES:

1. Two-File Comparison Mode:
   python compare_stacktraces.py --trace1 <file1> --trace2 <file2>

   What it does:
   - Loads stacktraces from two files (can contain multiple stacktraces separated by 80 dashes)
   - Pairs and compares corresponding stacktraces from each file (zip comparison)
   - Prints node chains for both traces and similarity percentage
   - Outputs detailed comparison results to console

2. Directory Pairwise Comparison Mode:
   python compare_stacktraces.py --trace_dir <directory> [--threshold <value>] [--output <file>]

   What it does:
   - Scans directory for all *_stacktrace.txt files
   - Extracts all stacktraces (with >= 8 lines) from each file
   - Performs pairwise comparison between stacktraces from DIFFERENT files
   - Filters and displays only comparisons with similarity >= threshold (default: 80%)
   - Saves ALL comparison results to JSON file (default: stacktrace_comparisons.json)
   - Outputs statistics: total comparisons and count above threshold

3. Directory Sequential Comparison Mode:
   python compare_stacktraces.py --trace_dir <directory> --seq [--threshold <value>]

   What it does:
   - Scans directory for all *_stacktrace.txt files
   - Extracts all stacktraces (with >= 8 lines) from each file
   - Sequentially builds a corpus of DISTINCT stacktraces
   - For each stacktrace, compares it with all stacktraces already in the corpus
   - Only adds to corpus if similarity with ALL existing corpus items is < threshold
   - Outputs: corpus size (distinct count), similar count, and total processed
   - Use case: Deduplicate stacktraces and identify unique error patterns

PARAMETERS:
- --trace1, --trace2: Paths to individual stacktrace files (Mode 1)
- --trace_dir: Directory containing *_stacktrace.txt files (Modes 2 & 3)
- --threshold: Similarity threshold percentage (default: 80.0)
- --output: JSON output file path (default: stacktrace_comparisons.json, Mode 2 only)
- --seq: Enable sequential comparison mode (Mode 3)

FILE FORMAT:
- Stacktrace files should contain Java stack traces with "at" prefixed frames
- Multiple stacktraces in a file should be separated by 80 dashes (-)
- Only stacktraces with >= 8 lines are processed

ALGORITHM:
1. Extract frames starting with "at " from stacktraces
2. Extract class prefix (before "$" or last ".")
3. Group consecutive frames with same prefix into nodes
4. Compute LCS similarity between node sequences
5. Return similarity as percentage (LCS length / max sequence length * 100)
"""

# ----------------------------------------------
# 1. Extract frames from raw Java stacktrace
# ----------------------------------------------


import argparse
import os
import json
from dataclasses import dataclass, asdict
from typing import List

def extract_frames(stacktrace: str):
    frames = []
    for line in stacktrace.splitlines():
        line = line.strip()
        if line.startswith("at "):
            frames.append(line)
    return frames


# ------------------------------------------------
# 2. Extract prefix (everything before "$")
#    Fallback: use class part before last "."
# ------------------------------------------------

def extract_prefix(frame_line: str):
    """
    Given: 'at reactor.core.publisher.FluxMapFuseable$MapFuseableSubscriber.onNext(FluxMapFuseable.java:129)'
    Return: 'reactor.core.publisher.FluxMapFuseable'
    """
    line = frame_line[3:]  # remove 'at '
    class_and_method = line.split("(")[0]  # remove "(File.java:x)"

    # Split into className and method
    if "." not in class_and_method:
        return class_and_method

    idx = class_and_method.rfind(".")
    full_class = class_and_method[:idx]

    # If class contains $, keep prefix before $
    if "$" in full_class:
        return full_class.split("$")[0]

    return full_class


# ---------------------------------------------------
# 3. Build "linked list" of nodes using prefix grouping
# ---------------------------------------------------

def build_node_chain(stacktrace: str):
    frames = extract_frames(stacktrace)

    # Process from bottom to top
    frames = frames[::-1]

    nodes = []
    last_prefix = None
    count = 0

    for f in frames:
        prefix = extract_prefix(f)

        if prefix == last_prefix:
            count += 1
        else:
            if last_prefix is not None:
                nodes.append((last_prefix, count))
            last_prefix = prefix
            count = 1

    # Add last node
    if last_prefix is not None:
        nodes.append((last_prefix, count))

    return nodes


# ----------------------------------------------
# 4. Compute LCS for two sequences
# ----------------------------------------------

def lcs_length(seq1, seq2):
    m = len(seq1)
    n = len(seq2)

    # dp table
    dp = [[0] * (n+1) for _ in range(m+1)]

    for i in range(1, m+1):
        for j in range(1, n+1):
            if seq1[i-1] == seq2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])

    return dp[m][n]


# ------------------------------------------------
# 5. Compute similarity between two node-chains
# ------------------------------------------------

def compute_similarity(nodes_a, nodes_b):
    seq_a = [prefix for (prefix, count) in nodes_a]
    seq_b = [prefix for (prefix, count) in nodes_b]

    if not seq_a or not seq_b:
        return 0.0

    lcs_len = lcs_length(seq_a, seq_b)
    max_len = max(len(seq_a), len(seq_b))
    similarity = lcs_len / max_len

    return similarity * 100.0  # percentage


# ------------------------------------------------
# 6. High-level convenience function
# ------------------------------------------------

def compare_stacktraces(trace1: str, trace2: str):
    nodes1 = build_node_chain(trace1)
    nodes2 = build_node_chain(trace2)

    similarity = compute_similarity(nodes1, nodes2)
    return nodes1, nodes2, similarity

# ------------------------------------------------
# 7. Extract multiple stacktraces from a file
# ------------------------------------------------

def extract_stacktraces_from_file(file_path: str):
    """Extract multiple stacktraces from a file separated by 80 dashes."""

    with open(file_path, 'r') as f:
        content = f.read()

    content = content.replace("linkerd-proxy,istio-proxy,vault-agent\n\n\n", "")
    stacktraces = content.split("-"*80)
    return stacktraces


# ------------------------------------------------
# 8. Stacktrace class for directory comparison
# ------------------------------------------------

@dataclass
class StackTrace:
    stacktrace: str
    filename: str


# ------------------------------------------------
# 9. Sequential comparison functions
# ------------------------------------------------

def compare_stacktrace_with_corpus(corpus: List[str], current_stacktrace: str, threshold: float) -> bool:
    """
    Compare a stacktrace with all stacktraces in the corpus.
    Returns True if the highest similarity is >= threshold, False otherwise.
    """
    if not corpus:
        return False

    max_similarity = 0.0
    for corpus_trace in corpus:
        _, _, similarity = compare_stacktraces(current_stacktrace, corpus_trace)
        max_similarity = max(max_similarity, similarity)

    return max_similarity >= threshold


def sequential_compare(all_stacktraces: List[StackTrace], threshold: float):
    """
    Sequentially compare stacktraces and build a corpus of distinct stacktraces.
    Only add a stacktrace to the corpus if its highest similarity with existing corpus is below threshold.
    """
    corpus: List[str] = []
    distinct_count = 0
    similar_count = 0

    print(f"Starting sequential comparison with threshold: {threshold}%\n")

    for st_obj in all_stacktraces:
        # Check if both stacktraces have at least 8 lines
        st_lines = len(st_obj.stacktrace.splitlines())

        if st_lines < 8:
            continue

        # Compare with corpus
        is_similar = compare_stacktrace_with_corpus(corpus, st_obj.stacktrace, threshold)

        if not is_similar:
            # Add to corpus as it's distinct
            corpus.append(st_obj.stacktrace)
            distinct_count += 1
            print(f"Added to corpus: {st_obj.filename} (Corpus size: {len(corpus)})")
        else:
            similar_count += 1

    print(f"\nSequential comparison complete:")
    print(f"Distinct stacktraces (corpus size): {distinct_count}")
    print(f"Similar stacktraces (skipped): {similar_count}")
    print(f"Total processed: {distinct_count + similar_count}")


# ------------------------------------------------
# Example Usage
# ------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare two Java stacktraces.")

    parser.add_argument("--trace1", type=str, help="Path to first stacktrace file")
    parser.add_argument("--trace2", type=str, help="Path to second stacktrace file")
    parser.add_argument("--trace_dir", type=str, help="Directory containing *_stacktrace.txt files")
    parser.add_argument("--threshold", type=float, default=80.0,
                        help="Similarity threshold for printing results (default: 80.0). Only used with --trace_dir")
    parser.add_argument("--output", type=str, default="stacktrace_comparisons.json",
                        help="Output JSON file for comparison results (default: stacktrace_comparisons.json). Only used with --trace_dir")
    parser.add_argument("--seq", action="store_true",
                        help="Use sequential comparison mode instead of pairwise comparison. Only used with --trace_dir")
    args = parser.parse_args()

    # Validate arguments: either (trace1 and trace2) or trace_dir
    if args.trace_dir:
        if args.trace1 or args.trace2:
            parser.error("--trace_dir cannot be used with --trace1 or --trace2")

        # Get all *_stacktrace.txt files from directory
        if not os.path.isdir(args.trace_dir):
            parser.error(f"Directory not found: {args.trace_dir}")

        stacktrace_files = [f for f in os.listdir(args.trace_dir) if f.endswith('_stacktrace.txt')]

        if not stacktrace_files:
            print(f"No *_stacktrace.txt files found in {args.trace_dir}")
            exit(1)

        # Extract all stacktraces from all files
        all_stacktraces: List[StackTrace] = []
        for filename in stacktrace_files:
            filepath = os.path.join(args.trace_dir, filename)
            stacktraces = extract_stacktraces_from_file(filepath)
            for st in stacktraces:
                st = st.strip()
                if st and len(st.splitlines()) >= 8:  # Only add stacktraces with at least 8 lines
                    all_stacktraces.append(StackTrace(stacktrace=st, filename=filename))

        print(f"Loaded {len(all_stacktraces)} stacktraces (>= 8 lines) from {len(stacktrace_files)} files")

        # Sort stacktraces by filename
        def sort_key(st: StackTrace):
            # Remove "_stacktrace.txt" and split by "_"
            filename_without_ext = st.filename.replace("_stacktrace.txt", "")
            parts = filename_without_ext.split("_")
            # Convert both parts to integers
            return (int(parts[0]), int(parts[1]))

        all_stacktraces.sort(key=sort_key)

        print(f"Threshold for printing: {args.threshold}%")
        if not args.seq:
            print(f"Output file: {args.output}")
        print()

        # Choose comparison mode based on --seq flag
        if args.seq:
            # Sequential comparison mode
            sequential_compare(all_stacktraces, args.threshold)
        else:
            # Pairwise comparison mode
            all_results = []
            comparison_count = 0
            above_threshold_count = 0

            for i in range(len(all_stacktraces)):
                for j in range(i + 1, len(all_stacktraces)):
                    st1 = all_stacktraces[i]
                    st2 = all_stacktraces[j]

                    # Only compare if from different files
                    if st1.filename != st2.filename:
                        nodes1, nodes2, similarity = compare_stacktraces(st1.stacktrace, st2.stacktrace)

                        comparison_count += 1

                        # Store result
                        result = {
                            "comparison_id": comparison_count,
                            "file1": st1.filename,
                            "file2": st2.filename,
                            "similarity": round(similarity, 2)
                        }
                        all_results.append(result)

                        # Only print if above threshold
                        if similarity >= args.threshold:
                            above_threshold_count += 1
                            print(f"Comparison #{comparison_count}")
                            print(f"File 1: {st1.filename}")
                            print(f"File 2: {st2.filename}")
                            print(f"Similarity: {similarity:.2f}%")
                            print("=" * 80 + "\n")

            # Save all results to JSON file
            with open(args.output, 'w') as f:
                json.dump(all_results, f, indent=2)

            print(f"Total comparisons: {comparison_count}")
            print(f"Comparisons above threshold ({args.threshold}%): {above_threshold_count}")
            print(f"All results saved to: {args.output}")

    elif args.trace1 and args.trace2:
        stacktraces_file1 = extract_stacktraces_from_file(args.trace1)
        stacktraces_file2 = extract_stacktraces_from_file(args.trace2)

        for st1, st2 in zip(stacktraces_file1, stacktraces_file2):
            trace1 = st1.strip()
            trace2 = st2.strip()

            if trace1 and trace2:
                nodes1, nodes2, similarity = compare_stacktraces(trace1, trace2)

                print("Nodes for Trace 1:")
                for n in nodes1:
                    print("  ", n)

                print("\nNodes for Trace 2:")
                for n in nodes2:
                    print("  ", n)

                print(f"\nSimilarity: {similarity:.2f}%")
                print("\n" + "="*80 + "\n")
    else:
        parser.error("Either --trace1 and --trace2, or --trace_dir must be provided")

