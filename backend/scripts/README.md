# Backend Scripts

`backend/scripts` has been reorganized by responsibility:

- `scripts/db/`: schema/data migration and database maintenance
- `scripts/data/`: background data collection and refresh jobs
- `scripts/dev/`: local diagnostics and performance experiments
- `scripts/dev/diagnostics/`: issue triage and one-off verification scripts

Backward compatibility:

- Legacy script paths in `scripts/*.py` are kept as wrappers.
- Legacy `tools/diagnostics/*.py` paths are also kept as wrappers.
- Existing commands continue to work.

Examples:

- `python backend/scripts/db/init_db.py`
- `python backend/scripts/data/auto_refresh_market_data.py`
- `python backend/scripts/dev/test_batch_collection.py`
