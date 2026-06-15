-- =============================================================================
-- Dashboard drill-down — supporting indexes
-- See plans/dashboard-drill-down.md (Stage B).
--
-- Deploy from a SQL client (sqlcmd, Azure Data Studio, az sql db query) against
-- the application database. Idempotent — safe to re-run.
--
-- Schema notes (verified against
-- infra/scripts/index_scripts/03_cu_process_data_text.py:294-315):
--   * processed_data.StartTime / EndTime are VARCHAR(255), NOT DATETIME.
--     Indexes target the raw varchar; queries CAST(... AS DATETIME) at
--     read time for DATE_BUCKET / DATEDIFF. At sample-data scale this still
--     yields seek+filter plans on the leading columns (mined_topic, sentiment,
--     key_phrase). If row counts grow large enough to expose the CAST as a
--     scan, follow up by promoting StartTime to a PERSISTED COMPUTED column of
--     type DATETIME and re-keying the index.
--   * processed_data exposes BOTH `mined_topic` (refined cluster name used by
--     the aggregate widgets) and `topic` (raw extraction). Drill on dimension
--     'topic' targets mined_topic.
--   * processed_data_key_phrases only has `topic` (no mined_topic) — drill on
--     dimension 'key_phrase' joins by key_phrase.
-- =============================================================================

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_processed_data_topic_sentiment_time'
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_processed_data_topic_sentiment_time
        ON [dbo].[processed_data] (mined_topic, sentiment, StartTime)
        INCLUDE (satisfied, EndTime, ConversationId);
    PRINT 'Created IX_processed_data_topic_sentiment_time';
END
ELSE
BEGIN
    PRINT 'IX_processed_data_topic_sentiment_time already exists — skipped';
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_processed_data_key_phrases_phrase_time'
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_processed_data_key_phrases_phrase_time
        ON [dbo].[processed_data_key_phrases] (key_phrase, StartTime)
        INCLUDE (ConversationId, sentiment, topic);
    PRINT 'Created IX_processed_data_key_phrases_phrase_time';
END
ELSE
BEGIN
    PRINT 'IX_processed_data_key_phrases_phrase_time already exists — skipped';
END
GO
