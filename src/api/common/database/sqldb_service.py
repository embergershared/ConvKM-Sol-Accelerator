from datetime import datetime
import struct

import pandas as pd
from pydantic import BaseModel
from api.models.input_models import ChartFilters
from common.config.config import Config
import logging
from helpers.azure_credential_utils import get_azure_credential_async
import pyodbc


class SQLTool(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    conn: pyodbc.Connection

    async def get_sql_response(self, sql_query: str) -> str:
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql_query)
            result = ''.join(str(row) for row in cursor.fetchall())
            return result
        except Exception as e:
            logging.error("Error executing SQL query: %s", e)
            return f"Error executing SQL query: {str(e)}"
        finally:
            if cursor:
                cursor.close()


async def get_db_connection():
    """Get a connection to the SQL database"""
    config = Config()

    server = config.sqldb_server
    database = config.sqldb_database
    mid_id = config.azure_client_id

    credential = None
    try:
        credential = await get_azure_credential_async(client_id=mid_id)
        token = await credential.get_token("https://database.windows.net/.default")
        token_bytes = token.token.encode("utf-16-LE")
        token_struct = struct.pack(
            f"<I{len(token_bytes)}s",
            len(token_bytes),
            token_bytes
        )
        SQL_COPT_SS_ACCESS_TOKEN = 1256

        installed_drivers = pyodbc.drivers()
        logging.info("Available ODBC drivers: %s", installed_drivers)

        conn = None
        last_error: Exception | None = None
        for driver in ["{ODBC Driver 18 for SQL Server}", "{ODBC Driver 17 for SQL Server}"]:
            driver_name = driver.strip("{}")
            if driver_name not in installed_drivers:
                logging.warning("Skipping %s: not installed in this container", driver_name)
                continue
            try:
                connection_string = (
                    f"DRIVER={driver};SERVER={server};DATABASE={database};"
                    "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
                )
                conn = pyodbc.connect(
                    connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct}
                )
                logging.info("Connected using Azure Credential with %s", driver)
                return conn
            except pyodbc.Error as exc:
                last_error = exc
                logging.exception("pyodbc.connect failed with %s: %s", driver, exc)
                continue

        if conn is None:
            raise RuntimeError(
                "Unable to connect using ODBC Driver 18 or 17 with Azure Credential"
            ) from last_error
        return conn
    except Exception as e:
        logging.error("Failed with Azure Credential: %s", str(e))
        raise RuntimeError("Unable to connect to SQL database using Microsoft Entra authentication.") from e
    finally:
        if credential and hasattr(credential, "close"):
            await credential.close()


async def adjust_processed_data_dates():
    """
    Adjusts the dates in the processed_data, km_processed_data, and processed_data_key_phrases tables
    to align with the current date.
    """
    conn = await get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        # Adjust the dates to the current date
        today = datetime.today()
        cursor.execute(
            "SELECT MAX(CAST(StartTime AS DATETIME)) FROM [dbo].[processed_data]"
        )
        max_start_time = (cursor.fetchone())[0]

        if max_start_time:
            days_difference = (today.date() - max_start_time.date()).days - 1
            if days_difference > 0:
                # Update processed_data table
                cursor.execute(
                    "UPDATE [dbo].[processed_data] SET StartTime = FORMAT(DATEADD(DAY, ?, StartTime), 'yyyy-MM-dd "
                    "HH:mm:ss'), EndTime = FORMAT(DATEADD(DAY, ?, EndTime), 'yyyy-MM-dd HH:mm:ss')",
                    (days_difference, days_difference)
                )
                # Update km_processed_data table
                cursor.execute(
                    "UPDATE [dbo].[km_processed_data] SET StartTime = FORMAT(DATEADD(DAY, ?, StartTime), 'yyyy-MM-dd "
                    "HH:mm:ss'), EndTime = FORMAT(DATEADD(DAY, ?, EndTime), 'yyyy-MM-dd HH:mm:ss')",
                    (days_difference, days_difference)
                )
                # Update processed_data_key_phrases table
                cursor.execute(
                    "UPDATE [dbo].[processed_data_key_phrases] SET StartTime = FORMAT(DATEADD(DAY, ?, StartTime), "
                    "'yyyy-MM-dd HH:mm:ss')", (days_difference,)
                )
                # Commit the changes
                conn.commit()
    finally:
        if cursor:
            cursor.close()
        conn.close()


async def fetch_filters_data():
    """
    Fetches filter data from the database and organizes it into a nested JSON structure.
    """
    conn = await get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        sql_stmt = '''select 'Topic' as filter_name, mined_topic as displayValue, mined_topic as key1 from
            (SELECT distinct mined_topic from processed_data) t
            union all
            select 'Sentiment' as filter_name, sentiment as displayValue, sentiment as key1 from
            (SELECT distinct sentiment from processed_data
            union all select 'all' as sentiment) t
            union all
            select 'Satisfaction' as filter_name, satisfied as displayValue, satisfied as key1 from
            (SELECT distinct satisfied from processed_data) t
            union all
            select 'Recording' as filter_name, recording_option as displayValue, recording_option as key1 from
            (SELECT 'all' as recording_option
            union all SELECT 'With Recording' as recording_option
            union all SELECT 'Without Recording' as recording_option) t
            union all
            select 'DateRange' as filter_name, date_range as displayValue, date_range as key1 from
            (SELECT 'Last 7 days' as date_range
            union all SELECT 'Last 14 days' as date_range
            union all SELECT 'Last 90 days' as date_range
            union all SELECT 'Year to Date' as date_range
            union all SELECT 'All time' as date_range
            ) t'''

        cursor.execute(sql_stmt)

        rows = [tuple(row) for row in cursor.fetchall()]

        # Define column names
        column_names = [i[0] for i in cursor.description]
        df = pd.DataFrame(rows, columns=column_names)
        df.rename(columns={'key1': 'key'}, inplace=True)

        nested_json = (
            df.groupby("filter_name")
            .apply(lambda x: {
                "filter_name": x.name,
                "filter_values": x.to_dict(orient="records")
            }, include_groups=False).to_list()
        )

        filters_data = nested_json

        return filters_data
    finally:
        if cursor:
            cursor.close()
        conn.close()


async def fetch_chart_data(chart_filters: ChartFilters = ''):
    """
    Fetches chart data from the database based on the provided filters and organizes it into a nested JSON structure.
    """
    conn = await get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        where_clause = ''
        req_body = ''
        try:
            req_body = chart_filters.model_dump()
        except Exception:  # model_dump may fail if filters are empty or invalid
            pass
        if req_body != '':
            where_clause = ''
            for key, value in req_body.items():
                if key == 'selected_filters':
                    for k, v in value.items():
                        if k == 'Topic':
                            topics = ''
                            for topic in v:
                                topics += f''' '{topic}', '''
                            if where_clause:
                                where_clause += " and "
                            if topics:
                                where_clause += f" mined_topic  in ({topics})"
                                where_clause = where_clause.replace(', )', ')')
                        elif k == 'Sentiment':
                            for sentiment in v:
                                if sentiment != 'all':
                                    if where_clause:
                                        where_clause += " and "
                                    where_clause += f"sentiment = '{sentiment}'"

                        elif k == 'Satisfaction':
                            for satisfaction in v:
                                if where_clause:
                                    where_clause += " and "
                                where_clause += f"satisfied = '{satisfaction}'"
                        elif k == 'DateRange':
                            for date_range in v:
                                if date_range == 'All time':
                                    pass  # no date filter
                                elif date_range == 'Last 7 days':
                                    if where_clause:
                                        where_clause += " and "
                                    where_clause += "StartTime >= DATEADD(day, -7, GETDATE())"
                                elif date_range == 'Last 14 days':
                                    if where_clause:
                                        where_clause += " and "
                                    where_clause += "StartTime >= DATEADD(day, -14, GETDATE())"
                                elif date_range == 'Last 90 days':
                                    if where_clause:
                                        where_clause += " and "
                                    where_clause += "StartTime >= DATEADD(day, -90, GETDATE())"
                                elif date_range == 'Year to Date':
                                    if where_clause:
                                        where_clause += " and "
                                    where_clause += "StartTime >= DATEADD(year, -1, GETDATE())"
                        elif k == 'Recording':
                            for recording in v:
                                if recording == 'With Recording':
                                    if where_clause:
                                        where_clause += " and "
                                    where_clause += "has_audio = 1"
                                elif recording == 'Without Recording':
                                    if where_clause:
                                        where_clause += " and "
                                    where_clause += "has_audio = 0"
        if where_clause:
            where_clause = f"where {where_clause} "

        sql_stmt = (
            f'''select 'TOTAL_CALLS' as id, 'Total Calls' as chart_name, 'card' as chart_type,
                'Total Calls' as name, count(*) as value, '' as unit_of_measurement from [dbo].[processed_data] {where_clause}
                union all
                select 'AVG_HANDLING_TIME' as id, 'Average Handling Time' as chart_name, 'card' as chart_type,
                'Average Handling Time' as name,
                AVG(DATEDIFF(MINUTE, StartTime, EndTime))  as value, 'mins' as unit_of_measurement from [dbo].[processed_data] {where_clause}
                union all
                select 'SATISFIED' as id, 'Satisfied' as chart_name, 'card' as chart_type, 'Satisfied' as name,
                round((CAST(SUM(CASE WHEN satisfied = 'yes' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100), 2) as value, '%' as unit_of_measurement from [dbo].[processed_data]
                {where_clause}
                union all
                select 'SENTIMENT' as id, 'Sentiment overview' as chart_name, 'donutchart' as chart_type,
                sentiment as name,
                (count(sentiment) * 100 / sum(count(sentiment)) over ()) as value,
                '' as unit_of_measurement from [dbo].[processed_data]  {where_clause}
                group by sentiment
                union all
                select 'AVG_HANDLING_TIME_BY_TOPIC' as id, 'Average Handling Time By Topic' as chart_name, 'bar' as chart_type,
                mined_topic as name,
                AVG(DATEDIFF(MINUTE, StartTime, EndTime)) as value, '' as unit_of_measurement from [dbo].[processed_data] {where_clause}
                group by mined_topic
                ''')

        # charts pt1
        cursor.execute(sql_stmt)

        # rows = cursor.fetchall()
        rows = [tuple(row) for row in cursor.fetchall()]

        column_names = [i[0] for i in cursor.description]
        df = pd.DataFrame(rows, columns=column_names)

        # charts pt1
        nested_json1 = (
            df.groupby(['id', 'chart_name', 'chart_type']).apply(
                lambda x: x[['name', 'value', 'unit_of_measurement']].to_dict(orient='records'), include_groups=False).reset_index()
        )
        nested_json1.columns = ['id', 'chart_name', 'chart_type', 'chart_value']
        result1 = nested_json1.to_dict(orient='records')
        sql_stmt = f'''SELECT TOP 1 WITH TIES
                        mined_topic as name, 'TOPICS' as id, 'Trending Topics' as chart_name, 'table' as chart_type,
                        lower(sentiment) as average_sentiment,
                        COUNT(*) AS call_frequency
                    FROM [dbo].[processed_data]
                    {where_clause}
                    GROUP BY mined_topic, sentiment
                    ORDER BY ROW_NUMBER() OVER (PARTITION BY mined_topic ORDER BY COUNT(*) DESC)
                    '''

        cursor.execute(sql_stmt)

        rows = [tuple(row) for row in cursor.fetchall()]

        column_names = [i[0] for i in cursor.description]
        df = pd.DataFrame(rows, columns=column_names)

        # charts pt2
        if not df.empty:
            nested_json2 = (
                df.groupby(['id', 'chart_name', 'chart_type']).apply(
                    lambda x: x[['name', 'call_frequency', 'average_sentiment']].to_dict(orient='records'),
                    include_groups=False
                ).reset_index()
            )
            nested_json2.columns = ['id', 'chart_name', 'chart_type', 'chart_value']
            result2 = nested_json2.to_dict(orient='records')
        else:
            result2 = []

        # For the key_phrases query, use a subquery to filter by has_audio via
        # processed_data since that column doesn't exist on processed_data_key_phrases.
        kp_where_clause = where_clause.replace('mined_topic', 'topic')
        has_audio_filter = ""
        if "has_audio = 1" in kp_where_clause:
            has_audio_filter = "ConversationId IN (SELECT ConversationId FROM processed_data WHERE has_audio = 1)"
            kp_where_clause = kp_where_clause.replace('has_audio = 1', has_audio_filter)
        elif "has_audio = 0" in kp_where_clause:
            has_audio_filter = "ConversationId IN (SELECT ConversationId FROM processed_data WHERE has_audio = 0)"
            kp_where_clause = kp_where_clause.replace('has_audio = 0', has_audio_filter)
        sql_stmt = f'''select top 15 key_phrase as text,
            'KEY_PHRASES' as id, 'Key Phrases' as chart_name, 'wordcloud' as chart_type,
            call_frequency as size, lower(average_sentiment) as average_sentiment from
            (
                SELECT TOP 1 WITH TIES
                key_phrase,
                sentiment as average_sentiment,
                COUNT(*) AS call_frequency from
                (
                    select key_phrase, sentiment from [dbo].[processed_data_key_phrases]
                    {kp_where_clause}
                ) t
                GROUP BY key_phrase, sentiment
                ORDER BY ROW_NUMBER() OVER (PARTITION BY key_phrase ORDER BY COUNT(*) DESC)
            ) t2
            order by call_frequency desc
            '''

        cursor.execute(sql_stmt)

        rows = [tuple(row) for row in cursor.fetchall()]

        column_names = [i[0] for i in cursor.description]
        df = pd.DataFrame(rows, columns=column_names)

        df = df.head(15)

        if not df.empty:
            nested_json3 = (
                df.groupby(['id', 'chart_name', 'chart_type']).apply(
                    lambda x: x[['text', 'size', 'average_sentiment']].to_dict(orient='records'),
                    include_groups=False
                ).reset_index()
            )
            nested_json3.columns = ['id', 'chart_name', 'chart_type', 'chart_value']
            result3 = nested_json3.to_dict(orient='records')
        else:
            result3 = []

        final_result = result1 + result2 + result3
        return final_result

    finally:
        if cursor:
            cursor.close()
        conn.close()


async def execute_sql_query(sql_query):
    """
    Executes a given SQL query and returns the result as a concatenated string.
    """
    conn = await get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql_query)
        result = ''.join(str(row) for row in cursor.fetchall())
        return result
    except Exception as e:
        logging.error("Error executing SQL query: %s", e)
        return None
    finally:
        if cursor:
            cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Dashboard drill-down — see plans/dashboard-drill-down.md (Stage B).
#
# Schema reminders (CREATE TABLE in
# infra/scripts/index_scripts/03_cu_process_data_text.py:294-315):
#   * processed_data.StartTime / EndTime are VARCHAR(255); cast to DATETIME at
#     read time for DATE_BUCKET / DATEDIFF.
#   * processed_data has BOTH `mined_topic` and `topic`; drill on dimension
#     'topic' targets mined_topic (matches aggregate widgets).
#   * processed_data_key_phrases only has `topic`; drill on dimension
#     'key_phrase' joins by key_phrase and surfaces topic from that table.
#
# Every function below uses bound `?` parameters via cursor.execute(sql, params).
# Do NOT extend the legacy string-concat `where_clause` builder in
# fetch_chart_data() — its sentiment / satisfaction interpolation is unsafe
# and only kept because the existing values come from an enum-restricted UI.
# ---------------------------------------------------------------------------

_DRILL_DATE_RANGE_DAYS = {
    "Last 7 days": 7,
    "Last 14 days": 14,
    "Last 90 days": 90,
}

# Anchor for weekly buckets: a Monday so weeks start Mon-Sun in DATE_BUCKET.
_DRILL_WEEK_ORIGIN = "2024-01-01"

_DRILL_SENTIMENT_SCORE_CASE = (
    "CASE LOWER(pd.sentiment) "
    "WHEN 'positive' THEN 1.0 "
    "WHEN 'negative' THEN -1.0 "
    "ELSE 0.0 END"
)


def _build_drill_filter_clauses(global_filters, table_alias: str = "pd"):
    """Translate a ChartFilters payload into bound WHERE fragments.

    Returns (clauses, params) where `clauses` is a list of SQL fragments (each
    referencing ? placeholders) and `params` is the matching value list. The
    caller joins clauses with ' AND ' and passes params to cursor.execute.

    Only the columns that exist on `processed_data` are emitted, so the same
    builder works for both the topic / sentiment path and the key-phrase join
    (which always projects via the processed_data alias).
    """
    if global_filters is None:
        return [], []
    try:
        payload = global_filters.model_dump()
    except Exception:
        return [], []
    selected = (payload or {}).get("selected_filters") or {}
    clauses: list[str] = []
    params: list = []

    topics = [t for t in (selected.get("Topic") or []) if t]
    if topics:
        placeholders = ", ".join(["?"] * len(topics))
        clauses.append(f"{table_alias}.mined_topic IN ({placeholders})")
        params.extend(topics)

    sentiments = [s for s in (selected.get("Sentiment") or []) if s and s != "all"]
    if sentiments:
        placeholders = ", ".join(["?"] * len(sentiments))
        clauses.append(f"{table_alias}.sentiment IN ({placeholders})")
        params.extend(sentiments)

    satisfactions = [s for s in (selected.get("Satisfaction") or []) if s]
    if satisfactions:
        placeholders = ", ".join(["?"] * len(satisfactions))
        clauses.append(f"{table_alias}.satisfied IN ({placeholders})")
        params.extend(satisfactions)

    for date_range in selected.get("DateRange") or []:
        days = _DRILL_DATE_RANGE_DAYS.get(date_range)
        if days:
            clauses.append(
                f"CAST({table_alias}.StartTime AS DATETIME) >= DATEADD(day, -?, GETDATE())"
            )
            params.append(days)
        elif date_range == "Year to Date":
            clauses.append(
                f"CAST({table_alias}.StartTime AS DATETIME) >= DATEFROMPARTS(YEAR(GETDATE()), 1, 1)"
            )

    recordings = [r for r in (selected.get("Recording") or []) if r and r != "all"]
    if recordings:
        for recording in recordings:
            if recording == "With Recording":
                clauses.append(f"ISNULL({table_alias}.has_audio, 0) = 1")
            elif recording == "Without Recording":
                clauses.append(f"ISNULL({table_alias}.has_audio, 0) = 0")

    return clauses, params


def _build_drill_selection_clause(dimension: str, value: str, table_alias: str = "pd"):
    """Translate the clicked chart element into a bound WHERE fragment.

    `dimension='key_phrase'` returns a clause targeting the joined key phrases
    table alias 'kp'; the caller is responsible for the JOIN.
    """
    if dimension == "topic":
        return f"{table_alias}.mined_topic = ?", [value]
    if dimension == "sentiment":
        return f"{table_alias}.sentiment = ?", [value]
    if dimension == "key_phrase":
        return "kp.key_phrase = ?", [value]
    raise ValueError(f"Unsupported drill dimension: {dimension}")


def _drill_from_clause(dimension: str) -> str:
    """Return the FROM/JOIN fragment. Aliases: pd, kp."""
    base = "[dbo].[processed_data] AS pd"
    if dimension == "key_phrase":
        return (
            f"{base} "
            "INNER JOIN [dbo].[processed_data_key_phrases] AS kp "
            "ON kp.ConversationId = pd.ConversationId"
        )
    return base


async def fetch_drill_timeseries(selection, bucket: str, global_filters) -> list[dict]:
    """L1 — time-bucketed aggregates for a single drill selection.

    Returns a list of dicts: bucket_start (ISO), calls, avg_sentiment_score,
    satisfied_pct, avg_handle_time_min.
    """
    if bucket not in ("day", "week"):
        raise ValueError(f"Unsupported bucket: {bucket}")

    sel_clause, sel_params = _build_drill_selection_clause(
        selection.dimension, selection.value
    )
    filter_clauses, filter_params = _build_drill_filter_clauses(global_filters)

    where = " AND ".join([sel_clause, *filter_clauses])

    # DATE_BUCKET (Azure SQL DB / SQL Server 2022+). The optional `origin`
    # argument must be a constant/literal — Azure SQL rejects a bound `?`
    # parameter there even though the leading args may be variables. The week
    # origin is a hardcoded module-level constant so inlining it as a SQL
    # literal is safe (no injection surface).
    if bucket == "day":
        bucket_expr = "DATE_BUCKET(day, 1, CAST(pd.StartTime AS DATETIME))"
    else:
        bucket_expr = (
            "DATE_BUCKET(week, 1, CAST(pd.StartTime AS DATETIME), "
            f"CAST('{_DRILL_WEEK_ORIGIN}' AS DATETIME))"
        )

    sql_stmt = f"""
        SELECT
            {bucket_expr} AS bucket_start,
            COUNT(*) AS calls,
            AVG({_DRILL_SENTIMENT_SCORE_CASE}) AS avg_sentiment_score,
            (CAST(SUM(CASE WHEN LOWER(pd.satisfied) = 'yes' THEN 1 ELSE 0 END) AS FLOAT)
                / NULLIF(COUNT(*), 0)) * 100.0 AS satisfied_pct,
            AVG(CAST(DATEDIFF(MINUTE, CAST(pd.StartTime AS DATETIME),
                                       CAST(pd.EndTime AS DATETIME)) AS FLOAT)) AS avg_handle_time_min
        FROM {_drill_from_clause(selection.dimension)}
        WHERE {where}
        GROUP BY {bucket_expr}
        ORDER BY bucket_start ASC
    """

    # The bucket expression appears twice (SELECT + GROUP BY) but has no
    # bound parameters — origin is inlined as a literal. See bucket_expr.
    params = sel_params + filter_params

    conn = await get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql_stmt, params)
        rows = cursor.fetchall()
        columns = [c[0] for c in cursor.description]
        result = []
        for row in rows:
            record = dict(zip(columns, row))
            bs = record.get("bucket_start")
            if isinstance(bs, datetime):
                record["bucket_start"] = bs.isoformat()
            for key in ("avg_sentiment_score", "satisfied_pct", "avg_handle_time_min"):
                v = record.get(key)
                if v is not None:
                    record[key] = float(v)
            result.append(record)
        return result
    finally:
        if cursor:
            cursor.close()
        conn.close()


async def fetch_drill_calls(
    selection, global_filters, time_range, offset: int, limit: int
) -> dict:
    """L2 — paginated call list for the drill selection (+ optional time bucket)."""
    sel_clause, sel_params = _build_drill_selection_clause(
        selection.dimension, selection.value
    )
    filter_clauses, filter_params = _build_drill_filter_clauses(global_filters)

    extra_clauses: list[str] = []
    extra_params: list = []
    if time_range is not None:
        # `from` is inclusive, `to` is exclusive (standard half-open interval).
        extra_clauses.append(
            "CAST(pd.StartTime AS DATETIME) >= CAST(? AS DATETIME)"
        )
        extra_params.append(time_range.from_)
        extra_clauses.append(
            "CAST(pd.StartTime AS DATETIME) < CAST(? AS DATETIME)"
        )
        extra_params.append(time_range.to)

    where = " AND ".join([sel_clause, *filter_clauses, *extra_clauses])

    base_from = _drill_from_clause(selection.dimension)
    base_params = sel_params + filter_params + extra_params

    if selection.dimension == "key_phrase":
        # Surface the per-call topic from the key-phrases table (which is the
        # only place dimension='key_phrase' filtering is meaningful).
        topic_col = "kp.topic"
        # De-dup at the call level — a single conversation may match many key
        # phrase rows; for the call list each conversation appears once.
        distinct = "DISTINCT"
    else:
        topic_col = "pd.mined_topic"
        distinct = ""

    count_stmt = f"""
        SELECT COUNT({'DISTINCT pd.ConversationId' if distinct else '*'}) AS total
        FROM {base_from}
        WHERE {where}
    """

    # Pagination uses OFFSET ... FETCH NEXT, which requires an ORDER BY.
    page_stmt = f"""
        SELECT {distinct}
            pd.ConversationId          AS conversation_id,
            CAST(pd.StartTime AS DATETIME) AS start_time,
            DATEDIFF(MINUTE, CAST(pd.StartTime AS DATETIME),
                              CAST(pd.EndTime AS DATETIME)) AS duration_min,
            pd.sentiment               AS sentiment,
            pd.satisfied               AS satisfied,
            {topic_col}                AS topic,
            pd.complaint               AS complaint,
            LEFT(ISNULL(pd.summary, ''), 80) AS summary_excerpt,
            ISNULL(pd.has_audio, 0)    AS has_audio
        FROM {base_from}
        WHERE {where}
        ORDER BY CAST(pd.StartTime AS DATETIME) DESC, pd.ConversationId DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    page_params = base_params + [offset, limit]

    conn = await get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(count_stmt, base_params)
        total_row = cursor.fetchone()
        total = int(total_row[0]) if total_row and total_row[0] is not None else 0

        cursor.execute(page_stmt, page_params)
        rows = cursor.fetchall()
        columns = [c[0] for c in cursor.description]
        items = []
        for row in rows:
            record = dict(zip(columns, row))
            st = record.get("start_time")
            if isinstance(st, datetime):
                record["start_time"] = st.isoformat()
            if record.get("duration_min") is not None:
                record["duration_min"] = int(record["duration_min"])
            items.append(record)
        return {"total": total, "items": items}
    finally:
        if cursor:
            cursor.close()
        conn.close()


async def fetch_call_detail(conversation_id: str) -> dict | None:
    """L3 — single call with its associated key phrases."""
    detail_stmt = """
        SELECT TOP 1
            pd.ConversationId          AS conversation_id,
            CAST(pd.StartTime AS DATETIME) AS start_time,
            CAST(pd.EndTime   AS DATETIME) AS end_time,
            DATEDIFF(MINUTE, CAST(pd.StartTime AS DATETIME),
                              CAST(pd.EndTime AS DATETIME)) AS duration_min,
            pd.sentiment               AS sentiment,
            pd.satisfied               AS satisfied,
            pd.mined_topic             AS topic,
            pd.complaint               AS complaint,
            pd.summary                 AS summary,
            pd.Content                 AS transcript_raw,
            ISNULL(pd.has_audio, 0)    AS has_audio
        FROM [dbo].[processed_data] AS pd
        WHERE pd.ConversationId = ?
    """
    phrases_stmt = """
        SELECT DISTINCT key_phrase
        FROM [dbo].[processed_data_key_phrases]
        WHERE ConversationId = ?
        ORDER BY key_phrase ASC
    """

    conn = await get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(detail_stmt, [conversation_id])
        row = cursor.fetchone()
        if row is None:
            return None
        columns = [c[0] for c in cursor.description]
        record = dict(zip(columns, row))
        for key in ("start_time", "end_time"):
            v = record.get(key)
            if isinstance(v, datetime):
                record[key] = v.isoformat()
        if record.get("duration_min") is not None:
            record["duration_min"] = int(record["duration_min"])

        cursor.execute(phrases_stmt, [conversation_id])
        record["key_phrases"] = [r[0] for r in cursor.fetchall() if r[0]]
        return record
    finally:
        if cursor:
            cursor.close()
        conn.close()
