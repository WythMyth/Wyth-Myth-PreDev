def merge_year_ranges(items):
    """
    items = list of dicts with from_date, to_date
    merges continuous or adjacent year ranges
    returns list of (start_date, end_date) sorted old → new
    """
    if not items:
        return []

    items = sorted(items, key=lambda x: x["from_date"])
    merged = []

    current_start = items[0]["from_date"]
    current_end = items[0]["to_date"]

    for item in items[1:]:
        next_start = item["from_date"]
        next_end = item["to_date"]

        if not (current_end and next_start):
            merged.append((current_start, current_end))
            current_start = next_start
            current_end = next_end
            continue

        # ALLOW SAME YEAR OR NEXT YEAR
        if next_start.year - current_end.year <= 1:
            current_end = max(current_end, next_end)
        else:
            merged.append((current_start, current_end))
            current_start = next_start
            current_end = next_end

    merged.append((current_start, current_end))
    return merged
