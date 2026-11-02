// NC Form 22 payroll normalization helpers.
// Purpose: establish the date-of-injury anchored 52-week reporting window and
// normalize payroll rows for later mapping to the official Form 22.

const DAY_MS = 24 * 60 * 60 * 1000;

function parseISODate(value, label = 'date') {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new TypeError(`${label} must use YYYY-MM-DD format`);
  }
  const [year, month, day] = value.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) {
    throw new RangeError(`${label} is not a valid calendar date`);
  }
  return date;
}

function toISO(date) {
  return date.toISOString().slice(0, 10);
}

export function form22ReportingWindow(dateOfInjury) {
  const injury = parseISODate(dateOfInjury, 'dateOfInjury');
  const end = new Date(injury.getTime() - DAY_MS); // day immediately before injury
  const start = new Date(injury.getTime() - (364 * DAY_MS)); // 52 weeks immediately preceding injury
  return { start: toISO(start), end: toISO(end), dateOfInjury: toISO(injury) };
}

export function normalizePayrollRows(rows, dateOfInjury) {
  if (!Array.isArray(rows)) throw new TypeError('rows must be an array');
  const window = form22ReportingWindow(dateOfInjury);
  const start = parseISODate(window.start).getTime();
  const end = parseISODate(window.end).getTime();

  return rows.map((row, index) => {
    if (!row || typeof row !== 'object') throw new TypeError(`row ${index + 1} must be an object`);
    const workDate = parseISODate(row.date, `row ${index + 1} date`);
    const amount = Number(row.amount ?? 0);
    if (!Number.isFinite(amount)) throw new TypeError(`row ${index + 1} amount must be numeric`);
    const paidInFull = row.paidInFull === undefined ? true : Boolean(row.paidInFull);
    const timestamp = workDate.getTime();
    return {
      date: toISO(workDate),
      amount,
      paidInFull,
      inReportingWindow: timestamp >= start && timestamp <= end,
      source: row.source ?? null
    };
  });
}

export function rowsForForm22(rows, dateOfInjury) {
  return normalizePayrollRows(rows, dateOfInjury).filter(row => row.inReportingWindow);
}
