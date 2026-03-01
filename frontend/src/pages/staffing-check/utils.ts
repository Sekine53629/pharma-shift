export interface DateEntry {
  date: string;
  dayOfWeek: number;       // JS convention: 0=Sun..6=Sat
  isSunday: boolean;
  isWeekend: boolean;      // Sat or Sun
  isHoliday: boolean;      // 祝日
  holidayName: string;     // '春分の日' etc., '' if none
}

// 日本の祝日マスタ (シフト期間に該当するもの)
const JAPANESE_HOLIDAYS: Record<string, string> = {
  '2026-01-01': '元日',
  '2026-01-12': '成人の日',
  '2026-02-11': '建国記念の日',
  '2026-02-23': '天皇誕生日',
  '2026-03-20': '春分の日',
  '2026-04-29': '昭和の日',
  '2026-05-03': '憲法記念日',
  '2026-05-04': 'みどりの日',
  '2026-05-05': 'こどもの日',
  '2026-07-20': '海の日',
  '2026-08-11': '山の日',
  '2026-09-21': '敬老の日',
  '2026-09-23': '秋分の日',
  '2026-10-12': 'スポーツの日',
  '2026-11-03': '文化の日',
  '2026-11-23': '勤労感謝の日',
};

export function getHolidayName(date: string): string {
  return JAPANESE_HOLIDAYS[date] ?? '';
}

function formatLocalDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function generateDateRange(start: string, end: string): DateEntry[] {
  const result: DateEntry[] = [];
  const current = new Date(start + 'T00:00:00');
  const last = new Date(end + 'T00:00:00');

  while (current <= last) {
    const dayOfWeek = current.getDay();
    const dateStr = formatLocalDate(current);
    const isSunday = dayOfWeek === 0;
    const hName = getHolidayName(dateStr);

    result.push({
      date: dateStr,
      dayOfWeek,
      isSunday,
      isWeekend: isSunday || dayOfWeek === 6,
      isHoliday: hName !== '',
      holidayName: hName,
    });
    current.setDate(current.getDate() + 1);
  }
  return result;
}

export function isPharmacistRole(role: string): boolean {
  return role === 'pharmacist' || role === 'managing_pharmacist';
}

/**
 * Convert JS Date.getDay() (0=Sun..6=Sat) to Python weekday (0=Mon..6=Sun).
 */
export function jsDayToPythonWeekday(jsDay: number): number {
  return jsDay === 0 ? 6 : jsDay - 1;
}
