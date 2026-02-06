import re


def parse_tat_to_hours(tat_text: str | None) -> int | None:
    """Parse various TAT string formats to approximate hours."""
    if not tat_text:
        return None

    text = tat_text.strip().lower()

    # "same day" variants
    if "same day" in text:
        return 12

    # "next day" variants
    if "next day" in text:
        return 24

    # "after X days" (Metropolis style)
    m = re.search(r"after\s+(\d+)\s+day", text)
    if m:
        return int(m.group(1)) * 24

    # "X day(s)" or "X working day(s)"
    m = re.search(r"(\d+)\s+(?:working\s+)?day", text)
    if m:
        return int(m.group(1)) * 24

    # "X hrs" or "X hours"
    m = re.search(r"(\d+)\s*(?:hrs?|hours?)", text)
    if m:
        return int(m.group(1))

    # Plain number (assume days)
    m = re.match(r"^(\d+)$", text)
    if m:
        return int(m.group(1)) * 24

    return None


def parse_tat_minutes_to_hours(minutes: str | int | None) -> int | None:
    """Convert TAT in minutes to hours."""
    if minutes is None:
        return None
    try:
        m = int(minutes)
        if m <= 0:
            return None
        return max(1, (m + 59) // 60)  # ceil division
    except (ValueError, TypeError):
        return None
