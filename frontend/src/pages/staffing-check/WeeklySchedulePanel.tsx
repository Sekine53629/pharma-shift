import React, { useCallback, useEffect, useState } from 'react';
import { bulkUpsertWeeklySchedules, fetchWeeklySchedules } from '../../api/endpoints';
import type { Store, StoreWeeklySchedule } from '../../types/models';

interface Props {
  store: Store;
  onSaved: () => void;
}

const DAY_LABELS = ['月', '火', '水', '木', '金', '土', '日'] as const;

interface DayState {
  is_open: boolean;
  open_time: string;
  close_time: string;
  staffing_delta: string;
}

const DEFAULT_OPEN: DayState = { is_open: true, open_time: '09:00', close_time: '18:00', staffing_delta: '0' };
const DEFAULT_CLOSED: DayState = { is_open: false, open_time: '', close_time: '', staffing_delta: '0' };

function defaultForDay(i: number): DayState {
  // Default: Mon-Sat open, Sun closed
  return i === 6 ? { ...DEFAULT_CLOSED } : { ...DEFAULT_OPEN };
}

const WeeklySchedulePanel: React.FC<Props> = ({ store, onSaved }) => {
  const [days, setDays] = useState<DayState[]>(Array.from({ length: 7 }, (_, i) => defaultForDay(i)));
  const [original, setOriginal] = useState<DayState[]>([]);
  const [holidayFlag, setHolidayFlag] = useState(false);
  const [originalHolidayFlag, setOriginalHolidayFlag] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetchWeeklySchedules({
          store: String(store.id),
          page_size: '10',
        });
        const data: StoreWeeklySchedule[] = res.data.results;
        const vals = Array.from({ length: 7 }, (_, i) => defaultForDay(i));
        for (const s of data) {
          vals[s.day_of_week] = {
            is_open: s.is_open,
            open_time: s.open_time ?? '',
            close_time: s.close_time ?? '',
            staffing_delta: s.staffing_delta,
          };
        }
        if (!cancelled) {
          setDays(vals);
          setOriginal(vals.map((d) => ({ ...d })));
          setHolidayFlag(store.operates_on_holidays);
          setOriginalHolidayFlag(store.operates_on_holidays);
          setMessage(null);
        }
      } catch {
        if (!cancelled) {
          setMessage({ text: '営業設定の読み込みに失敗しました', isError: true });
        }
      }
    };
    load();
    return () => { cancelled = true; };
  }, [store.id, store.operates_on_holidays]);

  const isDirty =
    holidayFlag !== originalHolidayFlag ||
    days.some((d, i) =>
      !original[i] ||
      d.is_open !== original[i].is_open ||
      d.open_time !== original[i].open_time ||
      d.close_time !== original[i].close_time ||
      d.staffing_delta !== original[i].staffing_delta
    );

  const updateDay = useCallback((idx: number, patch: Partial<DayState>) => {
    setDays((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], ...patch };
      return next;
    });
    setMessage(null);
  }, []);

  const handleSave = async () => {
    if (!isDirty) return;
    setSaving(true);
    setMessage(null);
    try {
      const schedules = days.map((d, i) => ({
        day_of_week: i,
        is_open: d.is_open,
        open_time: d.open_time || null,
        close_time: d.close_time || null,
        staffing_delta: d.staffing_delta || '0',
      }));
      await bulkUpsertWeeklySchedules(store.id, holidayFlag, schedules);
      setOriginal(days.map((d) => ({ ...d })));
      setOriginalHolidayFlag(holidayFlag);
      setMessage({ text: '営業設定を保存しました', isError: false });
      onSaved();
    } catch {
      setMessage({ text: '保存に失敗しました', isError: true });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.title}>店舗営業設定</span>
        <label style={styles.holidayLabel}>
          <input
            type="checkbox"
            checked={holidayFlag}
            onChange={(e) => { setHolidayFlag(e.target.checked); setMessage(null); }}
          />
          祝日営業
        </label>
        {isDirty && (
          <button
            onClick={handleSave}
            disabled={saving}
            style={{ ...styles.saveBtn, opacity: saving ? 0.6 : 1 }}
          >
            {saving ? '保存中...' : '保存'}
          </button>
        )}
        {message && (
          <span style={{ fontSize: 12, color: message.isError ? '#e94560' : '#27ae60' }}>
            {message.text}
          </span>
        )}
      </div>

      <div style={styles.grid}>
        {/* Header row */}
        <div style={styles.rowLabel} />
        {DAY_LABELS.map((label, i) => (
          <div key={i} style={{ ...styles.colHeader, color: i >= 5 ? '#e94560' : '#333' }}>
            {label}
          </div>
        ))}

        {/* 営業 row */}
        <div style={styles.rowLabel}>営業</div>
        {days.map((d, i) => (
          <div key={i} style={styles.cell}>
            <input
              type="checkbox"
              checked={d.is_open}
              onChange={(e) => updateDay(i, { is_open: e.target.checked })}
            />
          </div>
        ))}

        {/* 開店 row */}
        <div style={styles.rowLabel}>開店</div>
        {days.map((d, i) => (
          <div key={i} style={styles.cell}>
            {d.is_open ? (
              <input
                type="time"
                value={d.open_time}
                onChange={(e) => updateDay(i, { open_time: e.target.value })}
                style={styles.timeInput}
              />
            ) : (
              <span style={styles.disabledText}>—</span>
            )}
          </div>
        ))}

        {/* 閉店 row */}
        <div style={styles.rowLabel}>閉店</div>
        {days.map((d, i) => (
          <div key={i} style={styles.cell}>
            {d.is_open ? (
              <input
                type="time"
                value={d.close_time}
                onChange={(e) => updateDay(i, { close_time: e.target.value })}
                style={styles.timeInput}
              />
            ) : (
              <span style={styles.disabledText}>—</span>
            )}
          </div>
        ))}

        {/* 人工調整 row */}
        <div style={styles.rowLabel}>人工調整</div>
        {days.map((d, i) => (
          <div key={i} style={styles.cell}>
            {d.is_open ? (
              <input
                type="number"
                step="0.5"
                min="-5"
                max="5"
                value={d.staffing_delta}
                onChange={(e) => updateDay(i, { staffing_delta: e.target.value })}
                style={styles.deltaInput}
              />
            ) : (
              <span style={styles.disabledText}>—</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  panel: {
    border: '1px solid #ddd',
    borderRadius: 6,
    padding: '12px 16px',
    marginBottom: 16,
    background: '#fafafa',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
    flexWrap: 'wrap',
  },
  title: {
    fontSize: 13,
    fontWeight: 600,
    color: '#333',
  },
  holidayLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    fontSize: 13,
    color: '#555',
    cursor: 'pointer',
  },
  saveBtn: {
    padding: '4px 12px',
    background: '#0f3460',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    fontSize: 12,
    cursor: 'pointer',
    fontWeight: 600,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '56px repeat(7, 1fr)',
    gap: '4px 6px',
    alignItems: 'center',
  },
  rowLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: '#555',
    textAlign: 'right',
    paddingRight: 4,
  },
  colHeader: {
    fontSize: 12,
    fontWeight: 600,
    textAlign: 'center',
  },
  cell: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  timeInput: {
    width: 72,
    padding: '2px 4px',
    border: '1px solid #ddd',
    borderRadius: 4,
    fontSize: 12,
    textAlign: 'center',
  },
  deltaInput: {
    width: 50,
    padding: '2px 4px',
    border: '1px solid #ddd',
    borderRadius: 4,
    fontSize: 12,
    textAlign: 'center',
  },
  disabledText: {
    color: '#bbb',
    fontSize: 12,
  },
};

export default WeeklySchedulePanel;
