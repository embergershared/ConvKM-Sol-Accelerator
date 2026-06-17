"""Adjust audio record dates to align with the sample data date range.

Shifts all has_audio=1 records forward so they appear within the same
time window as the transcript-only records (which get date-shifted by
the app's adjust_processed_data_dates on startup).

Usage:
    python3 infra/scripts/index_scripts/05_adjust_audio_dates.py \
        --sql_server <FQDN> --sql_database <name>
"""
import argparse
import struct
import pyodbc
from azure.identity import AzureCliCredential

parser = argparse.ArgumentParser(description="Adjust audio record dates")
parser.add_argument("--sql_server", required=True)
parser.add_argument("--sql_database", required=True)
args = parser.parse_args()

credential = AzureCliCredential()

# Connect to SQL (same pattern as 04_cu_process_custom_data.py)
try:
    driver = "{ODBC Driver 18 for SQL Server}"
    token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("utf-16-LE")
    token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
    SQL_COPT_SS_ACCESS_TOKEN = 1256
    connection_string = f"DRIVER={driver};SERVER={args.sql_server};DATABASE={args.sql_database};"
    conn = pyodbc.connect(connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
except Exception:
    driver = "{ODBC Driver 17 for SQL Server}"
    token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("utf-16-LE")
    token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
    SQL_COPT_SS_ACCESS_TOKEN = 1256
    connection_string = f"DRIVER={driver};SERVER={args.sql_server};DATABASE={args.sql_database};"
    conn = pyodbc.connect(connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})

cursor = conn.cursor()

# Find how far behind the audio records are relative to the rest
cursor.execute('''
    SELECT MAX(CAST(StartTime AS DATETIME)) AS max_all,
           MAX(CASE WHEN has_audio = 1 THEN CAST(StartTime AS DATETIME) END) AS max_audio
    FROM [dbo].[processed_data]
''')
row = cursor.fetchone()
max_all, max_audio = row[0], row[1]

if max_audio and max_all and max_audio < max_all:
    days_shift = (max_all - max_audio).days
    if days_shift > 0:
        cursor.execute('''
            UPDATE [dbo].[processed_data]
            SET StartTime = FORMAT(DATEADD(DAY, ?, CAST(StartTime AS DATETIME)), 'yyyy-MM-dd HH:mm:ss'),
                EndTime = FORMAT(DATEADD(DAY, ?, CAST(EndTime AS DATETIME)), 'yyyy-MM-dd HH:mm:ss')
            WHERE has_audio = 1
        ''', (days_shift, days_shift))
        audio_count = cursor.rowcount
        cursor.execute('''
            UPDATE [dbo].[processed_data_key_phrases]
            SET StartTime = FORMAT(DATEADD(DAY, ?, CAST(StartTime AS DATETIME)), 'yyyy-MM-dd HH:mm:ss')
            WHERE ConversationId IN (SELECT ConversationId FROM processed_data WHERE has_audio = 1)
        ''', (days_shift,))
        conn.commit()
        print(f"  Shifted {audio_count} audio records forward by {days_shift} days")
    else:
        print("  Audio dates already in range, no adjustment needed")
else:
    print("  No audio records to adjust (or no gap detected)")

cursor.close()
conn.close()
