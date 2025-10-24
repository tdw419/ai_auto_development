# Troubleshooting 🛠️

## Common Issues

### `ValueError: Invalid isoformat string`
- Ensure the input string follows ISO 8601.
- Use `to_iso_format` when storing timestamps.

### `TypeError: can't compare offset-naive and offset-aware datetimes`
- Mix of naive and aware datetimes detected.
- Use `get_current_utc_time` instead of `datetime.now()`.

### `ModuleNotFoundError: No module named 'vista_time'`
- Confirm installation with `pip show vista-time-utils`.
- Check that the active virtual environment is correct.

### CI Fails on Python 3.9
- Use `Optional[...]` instead of the `|` union operator to maintain compatibility.
- Ensure tests cover all supported Python versions.

## Getting Help

- File an issue on GitHub: <https://github.com/tdw419/ai_auto_development/issues>
- Join discussions in the repository for roadmap planning.
