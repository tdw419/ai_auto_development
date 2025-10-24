# Frequently Asked Questions ❓

### Does this package handle daylight saving time?

Yes. All operations use UTC to avoid DST pitfalls. Convert to local time only when displaying to users.

### Why not use `datetime.utcnow()`?

`datetime.utcnow()` returns a naive datetime (no timezone). `vista_time` always returns timezone-aware values.

### Can I use this with pandas?

Absolutely. Use `from_iso_format` to parse and then convert to pandas `Timestamp` as needed.

### Is there support for async applications?

Yes. The utilities are synchronous but can be used anywhere (including async code) because they are pure functions without I/O.

### How do I migrate gradually?

Leverage `vista_time.compat.legacy_shim` to provide a drop-in interface while incrementally replacing imports.
