import os

import pandas as pd

from tqdm import tqdm

df = pd.read_csv("runrequests_of_top_SLXs_with_most_occurrences_applog_stacktrace_12dec.csv")
dir_path = './downloads/'

pbar = tqdm(total=len(df), desc="Grouping files into SLX aliases")
for _, row in df.iterrows():
    slx_name = row['SLX Alias']
    runsession_id = row['Runsession ID']
    runrequests = row['RunRequest IDs'].split(',')

    slx_dir = os.path.join(dir_path, slx_name)
    os.makedirs(slx_dir, exist_ok=True)
    
    
    for runrequest in runrequests:
        report_file_name = f'{runsession_id}_{runrequest}_report.jsonl'
        log_file_name = f'{runsession_id}_{runrequest}_log.html'

        if os.path.exists(os.path.join(dir_path, report_file_name)):
            os.rename(
                os.path.join(dir_path, report_file_name),
                os.path.join(slx_dir, report_file_name)
            )
        if os.path.exists(os.path.join(dir_path, log_file_name)):
            os.rename(
                os.path.join(dir_path, log_file_name),
                os.path.join(slx_dir, log_file_name)
            )
    
    pbar.update(1)
pbar.close()