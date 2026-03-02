"""Re-export shared markdown parser for backward compatibility."""
from shared.utils.markdown_parser import (
    parse_markdown,
    extract_title,
    estimate_reading_time,
    extract_excerpt,
    parse_markdown_cached,
)
