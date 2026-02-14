# Package Wiring Audit: services

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `services`

Files checked: 7
- WIRED: 0
- PARTIAL: 2
- ORPHAN: 4
- ENTRYPOINT: 0
- TEST_ONLY: 1

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `services/mac_tasks.py` | 0 | 0 | - | - | ORPHAN |
| `services/ocr_engine.py` | 0 | 0 | - | - | ORPHAN |
| `services/pdf_engine.py` | 0 | 0 | - | - | ORPHAN |
| `services/slack_files.py` | 2 | 0 | - | - | PARTIAL |
| `services/tool_feedback_service.py` | 2 | 1 | Y | - | PARTIAL |
| `services/tool_learning_engine.py` | 0 | 1 | Y | - | TEST |
| `services/tool_learning_scheduler.py` | 0 | 0 | - | - | ORPHAN |

## Level C: API Instantiation — `services`

API Status: **SHOULD_HAVE_API**
Symbols checked: 26
- USED: 11
- TEST_ONLY: 2
- UNUSED: 13

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `ocr_image` | 0 | 0 | UNUSED |
| `ocr_pdf_first_page` | 0 | 0 | UNUSED |
| `extract_pdf` | 0 | 0 | UNUSED |
| `save_to_s3` | 0 | 0 | UNUSED |
| `get_s3_presigned_url` | 0 | 0 | UNUSED |
| `download_file` | 0 | 0 | UNUSED |
| `save_to_disk` | 0 | 0 | UNUSED |
| `save_file` | 0 | 0 | UNUSED |
| `build_artifact_record` | 0 | 0 | UNUSED |
| `build_artifact_record_legacy` | 0 | 0 | UNUSED |
| `process_slack_file` | 0 | 0 | UNUSED |
| `ToolFeedbackService` | 0 | 1 | TEST_ONLY |
| `ToolHealthSnapshot` | 0 | 0 | UNUSED |
| `ToolLearningEngine` | 0 | 1 | TEST_ONLY |
| `register_tool_learning_jobs` | 0 | 0 | UNUSED |

**Recommended `__all__` entries (used externally):**
- `MacTask`
- `ToolFeedbackEntry`
- `complete_task`
- `enqueue_mac_task`
- `enqueue_task`
- `get_file_info`
- `get_next_task`
- `get_tool_feedback_service`
- `list_tasks`
- `mark_task_completed`
- `process_file_attachments`
