def describe_source(sheet: str | None) -> str:
    """Name the thing an error is about; CSV files have no sheet name."""
    return f"Sheet '{sheet}'" if sheet else "File"
