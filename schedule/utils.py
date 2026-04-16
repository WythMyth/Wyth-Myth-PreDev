"""
utils.py  –  Recurring-meeting date generator
(No external dependencies beyond the standard library.)
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class RecurrenceSpec:
    start_date: date
    recurrence_type: str          # daily | weekly | monthly | yearly
    interval: int

    days_of_week: list[int] | None = None        # 0=Sun … 6=Sat

    monthly_mode: str | None = None              # day_of_month | nth_weekday
    monthly_day_of_month: int | None = None
    monthly_nth: int | None = None               # 1-5 or 6=last
    monthly_weekday: int | None = None           # 0=Sun … 6=Sat

    yearly_mode: str | None = None               # day_of_month | nth_weekday
    yearly_month: int | None = None              # 1-12
    yearly_day_of_month: int | None = None
    yearly_nth: int | None = None
    yearly_weekday: int | None = None

    end_mode: str | None = None                  # "on" | "after"
    end_on_date: date | None = None
    end_after_occurrences: int | None = None


# ── Internal helpers ───────────────────────────────────────────────────────

def _last_day_of_month(y: int, m: int) -> int:
    return calendar.monthrange(y, m)[1]


def _clamp_day(y: int, m: int, d: int) -> date:
    return date(y, m, min(d, _last_day_of_month(y, m)))


def _add_months(dt: date, months: int) -> date:
    y = dt.year + (dt.month - 1 + months) // 12
    m = (dt.month - 1 + months) % 12 + 1
    return _clamp_day(y, m, dt.day)


def _weekday_sun0(dt: date) -> int:
    """Mon=0…Sun=6 → Sun=0…Sat=6"""
    return (dt.weekday() + 1) % 7


def _last_weekday_in_month(y: int, m: int, weekday_sun0: int) -> date:
    last = date(y, m, _last_day_of_month(y, m))
    back = (_weekday_sun0(last) - weekday_sun0) % 7
    return last - timedelta(days=back)


def _nth_weekday_in_month(y: int, m: int, nth: int, weekday_sun0: int) -> date:
    if nth == 6:
        return _last_weekday_in_month(y, m, weekday_sun0)
    first = date(y, m, 1)
    delta = (weekday_sun0 - _weekday_sun0(first)) % 7
    target = first + timedelta(days=delta + 7 * (nth - 1))
    if target.month != m:
        return _last_weekday_in_month(y, m, weekday_sun0)
    return target


# ── Generators ─────────────────────────────────────────────────────────────

def _gen_daily(spec: RecurrenceSpec, limit: int) -> list[date]:
    out, cur, step = [], spec.start_date, timedelta(days=spec.interval)
    while len(out) < limit:
        out.append(cur)
        cur += step
    return out


def _gen_weekly(spec: RecurrenceSpec, end_date: date | None, limit: int) -> list[date]:
    out, cur = [], spec.start_date
    days = sorted(set(spec.days_of_week or []))
    if not days:
        return out
    while len(out) < limit:
        if end_date and cur > end_date:
            break
        weeks_since = (cur - spec.start_date).days // 7
        if weeks_since % spec.interval == 0 and _weekday_sun0(cur) in days:
            out.append(cur)
        cur += timedelta(days=1)
        if end_date is None and (cur - spec.start_date).days > 3650:
            break
    return out


def _gen_monthly_day(spec: RecurrenceSpec, end_date: date | None, limit: int) -> list[date]:
    out, i = [], 0
    dom = spec.monthly_day_of_month or spec.start_date.day
    while len(out) < limit:
        base = _add_months(spec.start_date.replace(day=1), i * spec.interval)
        d = _clamp_day(base.year, base.month, dom)
        if d < spec.start_date:
            i += 1; continue
        if end_date and d > end_date:
            break
        out.append(d); i += 1
    return out


def _gen_monthly_nth(spec: RecurrenceSpec, end_date: date | None, limit: int) -> list[date]:
    out, i = [], 0
    nth = spec.monthly_nth or 1
    wd  = spec.monthly_weekday if spec.monthly_weekday is not None else _weekday_sun0(spec.start_date)
    while len(out) < limit:
        base = _add_months(spec.start_date.replace(day=1), i * spec.interval)
        d = _nth_weekday_in_month(base.year, base.month, nth, wd)
        if d < spec.start_date:
            i += 1; continue
        if end_date and d > end_date:
            break
        out.append(d); i += 1
    return out


def _gen_yearly_day(spec: RecurrenceSpec, end_date: date | None, limit: int) -> list[date]:
    out, i = [], 0
    month = spec.yearly_month or spec.start_date.month
    dom   = spec.yearly_day_of_month or spec.start_date.day
    while len(out) < limit:
        y = spec.start_date.year + i * spec.interval
        d = _clamp_day(y, month, dom)
        if d < spec.start_date:
            i += 1; continue
        if end_date and d > end_date:
            break
        out.append(d); i += 1
    return out


def _gen_yearly_nth(spec: RecurrenceSpec, end_date: date | None, limit: int) -> list[date]:
    out, i = [], 0
    month = spec.yearly_month or spec.start_date.month
    nth   = spec.yearly_nth or 1
    wd    = spec.yearly_weekday if spec.yearly_weekday is not None else _weekday_sun0(spec.start_date)
    while len(out) < limit:
        y = spec.start_date.year + i * spec.interval
        d = _nth_weekday_in_month(y, month, nth, wd)
        if d < spec.start_date:
            i += 1; continue
        if end_date and d > end_date:
            break
        out.append(d); i += 1
    return out


# ── Public API ─────────────────────────────────────────────────────────────

def generate_occurrence_dates(spec: RecurrenceSpec, hard_cap: int = 1000) -> list[date]:
    """Return a list of occurrence dates according to *spec*."""
    if spec.interval < 1:
        raise ValueError("interval must be >= 1")

    if spec.end_mode == "after":
        if not spec.end_after_occurrences or spec.end_after_occurrences < 1:
            raise ValueError("end_after_occurrences required")
        limit, end_date = min(spec.end_after_occurrences, hard_cap), None
    elif spec.end_mode == "on":
        if not spec.end_on_date:
            raise ValueError("end_on_date required")
        if spec.end_on_date < spec.start_date:
            raise ValueError("end_on_date cannot be before start_date")
        limit, end_date = hard_cap, spec.end_on_date
    else:
        raise ValueError("end_mode must be 'on' or 'after'")

    rt = spec.recurrence_type
    if rt == "daily":
        dates = _gen_daily(spec, limit)
        if end_date:
            dates = [d for d in dates if d <= end_date]
        return dates[:hard_cap]
    if rt == "weekly":
        return _gen_weekly(spec, end_date, limit)[:hard_cap]
    if rt == "monthly":
        if spec.monthly_mode == "day_of_month":
            return _gen_monthly_day(spec, end_date, limit)[:hard_cap]
        if spec.monthly_mode == "nth_weekday":
            return _gen_monthly_nth(spec, end_date, limit)[:hard_cap]
        raise ValueError("monthly_mode required for monthly recurrence")
    if rt == "yearly":
        if spec.yearly_mode == "day_of_month":
            return _gen_yearly_day(spec, end_date, limit)[:hard_cap]
        if spec.yearly_mode == "nth_weekday":
            return _gen_yearly_nth(spec, end_date, limit)[:hard_cap]
        raise ValueError("yearly_mode required for yearly recurrence")
    raise ValueError(f"invalid recurrence_type: {rt!r}")