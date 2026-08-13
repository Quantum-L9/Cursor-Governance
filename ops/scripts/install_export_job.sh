#!/usr/bin/env bash
# RETIRED 2026-08-13 — do not reinstall hourly chat export.
# Replacement: sessionEnd → ops.graphiti.hydration.archive_transcript → S3
echo "RETIRED: install_export_job.sh will not install com.tenx.chat-export." >&2
launchctl bootout "gui/$(id -u)/com.tenx.chat-export" 2>/dev/null || true
exit 0
