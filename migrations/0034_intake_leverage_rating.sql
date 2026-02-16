-- =============================================================================
-- L9 Memory Substrate - Intake rating uses importance_score (observe cycle)
-- Migration: 0034_intake_leverage_rating.sql
-- Date: 2026-02-14
-- =============================================================================
--
-- PURPOSE: Document that task-intake leverage/ROI rating uses existing
--   importance_score (migration 0008). No new columns.
--
-- USAGE: At task intake, set metadata.importance (or metadata.importance_score)
--   on PacketEnvelopeIn; repository already persists it to packet_store.importance_score.
--   Foresight run_observe_cycle() queries packet_store ORDER BY importance_score DESC
--   for highest-leverage candidate tasks.
--
-- DEPENDENCIES: 0001–0033 applied.
-- =============================================================================

-- Clarify that importance_score is used for intake/leverage rating (observe cycle)
COMMENT ON COLUMN packet_store.importance_score IS 'Learned importance (0.0-1.0). Also used as intake/leverage rating at task intake when set via metadata.importance.';

-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 0034 completed: importance_score documented as intake/leverage rating';
END $$;
