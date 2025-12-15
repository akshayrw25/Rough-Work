# Applog Pattern Exploration

Explore top 100 SLXs that have the most occurrences in wba-rxi-prod for *analyze application log patterns* or *analyze workload stacktraces* issues.

## Overview

This project contains utilities for analyzing and comparing Java stacktraces from application logs. The workflow involves downloading report files, organizing them by SLX alias, extracting stacktraces, and performing similarity analysis.

## Scripts

### 1. group_files_into_slx_alias.py

Organizes downloaded report and log files by SLX alias for easier analysis.

**Purpose**: Reads a CSV file containing SLX information and moves downloaded files from a flat `downloads/` directory into subdirectories named by SLX alias.

**Input**:
- CSV file: `runrequests_of_top_SLXs_with_most_occurrences_applog_stacktrace_12dec.csv`
- Downloaded files in `./downloads/` directory

**Output**: Files organized into `./downloads/{slx_alias}/` subdirectories

**Dependencies**:
- pandas
- tqdm

**Usage**:
```bash
python group_files_into_slx_alias.py
```

### 2. extract_stacktraces.py

Extracts and normalizes stacktraces from JSONL report files.

**Purpose**: Parses the last JSON object in a `.jsonl` file, extracts the stacktrace section after `**Excluded Containers:**`, removes timestamp prefixes, and saves as a clean text file.

**Input**: JSONL report file (e.g., `{runsession_id}_{runrequest_id}_report.jsonl`)

**Output**: Text file with extracted stacktrace (e.g., `{runsession_id}_{runrequest_id}_stacktrace.txt`)

**Usage**:
```bash
python extract_stacktraces.py someprefix_someid_report.jsonl
```

**Features**:
- Extracts text after `**Excluded Containers:**` delimiter
- Strips timestamp prefixes (format: `YYYY-MM-DDTHH:MM:SS.nnnnnnnnnZ`)
- Outputs clean stacktrace text for analysis

### 3. compare_stacktraces.py

Compares Java stacktraces using Longest Common Subsequence (LCS) similarity scoring.

**Purpose**: Analyzes two stacktraces by grouping stack frames by class prefix and computing similarity percentage using LCS algorithm.

**Input**: Two stacktrace files (text format)

**Output**:
- Node chains (grouped frames) for each stacktrace
- Similarity percentage (0-100%)

**Usage**:
```bash
python compare_stacktraces.py --trace1 <trace1_file> --trace2 <trace2_file>
```

**Features**:
- Extracts stack frames (lines starting with "at ")
- Groups consecutive frames by class prefix (before `$` or last `.`)
- Handles multiple stacktraces per file (separated by 80 dashes)
- Computes LCS-based similarity metric
- Outputs detailed node chains showing frame groupings

**Algorithm**:
1. Extract frames from stacktraces
2. Build node chains by grouping consecutive frames with same class prefix
3. Compute LCS length between the two node sequences
4. Calculate similarity as: `(LCS_length / max_length) * 100`

## Workflow

1. **Organize files**: Run `group_files_into_slx_alias.py` to organize downloaded files by SLX
2. **Extract stacktraces**: Use `extract_stacktraces.py` on each JSONL report file
3. **Compare stacktraces**: Use `compare_stacktraces.py` to analyze similarity between stacktraces

## Example

```bash
# Step 1: Organize downloads
python group_files_into_slx_alias.py

# Step 2: Extract stacktraces from reports
python extract_stacktraces.py downloads/my-slx-alias/12345_67890_report.jsonl

# Step 3: Compare extracted stacktraces
python compare_stacktraces.py --trace1 file1_stacktrace.txt --trace2 file2_stacktrace.txt
```
