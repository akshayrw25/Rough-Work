"""
Compare two Java stacktraces by extracting frames, grouping by class prefixes, 
and computing similarity using Longest Common Subsequence (LCS).
"""

# ----------------------------------------------
# 1. Extract frames from raw Java stacktrace
# ----------------------------------------------


import argparse

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
# Example Usage
# ------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare two Java stacktraces.")
    
    parser.add_argument("--trace1", type=str, required=True, help="Path to first stacktrace file")
    parser.add_argument("--trace2", type=str, required=True, help="Path to second stacktrace file")
    args = parser.parse_args()

    if args.trace1 and args.trace2:
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
        print(parser.print_help())

    
