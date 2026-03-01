import React, { useState } from 'react';
import { createShift, updateShift } from '../../api/endpoints';
import { parseApiError } from '../../api/parseApiError';
import type { Shift, ShiftPeriod, Staff } from '../../types/models';

interface Props {
  shift?: Shift;
  staffList: Staff[];
  periods: ShiftPeriod[];
  selectedPeriodId?: string;
  defaultDate?: string;
  onSaved: () => void;
  onCancel: () => void;
}

const ShiftForm: React.FC<Props> = ({
  shift,
  staffList,
  periods,
  selectedPeriodId,
  defaultDate,
  onSaved,
  onCancel,
}) => {
  const isEdit = !!shift;

  const [staffId, setStaffId] = useState(shift ? String(shift.staff) : '');
  const [periodId, setPeriodId] = useState(
    shift ? String(shift.shift_period) : selectedPeriodId ?? '',
  );
  const [date, setDate] = useState(shift?.date ?? defaultDate ?? '');
  const [shiftType, setShiftType] = useState<string>(shift?.shift_type ?? 'full');
  const [leaveType, setLeaveType] = useState(shift?.leave_type ?? '');
  const [note, setNote] = useState(shift?.note ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');

    const payload: Partial<Shift> = {
      staff: Number(staffId),
      shift_period: Number(periodId),
      date,
      shift_type: shiftType as Shift['shift_type'],
      leave_type: leaveType || null,
      note,
    };

    try {
      if (isEdit) {
        await updateShift(shift!.id, payload);
      } else {
        await createShift(payload);
      }
      onSaved();
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <div style={styles.title}>{isEdit ? `Edit Shift: ${shift!.staff_name}` : 'Add Shift'}</div>

      {error && <div style={styles.error}>{error}</div>}

      <div style={styles.row}>
        <label style={styles.label}>
          Staff
          <select
            style={styles.input}
            value={staffId}
            onChange={(e) => setStaffId(e.target.value)}
            required
          >
            <option value="">-- Select --</option>
            {staffList.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>

        <label style={styles.label}>
          Period
          <select
            style={styles.input}
            value={periodId}
            onChange={(e) => setPeriodId(e.target.value)}
            required
          >
            <option value="">-- Select --</option>
            {periods.map((p) => (
              <option key={p.id} value={p.id}>
                {p.start_date} ~ {p.end_date}
              </option>
            ))}
          </select>
        </label>

        <label style={styles.label}>
          Date
          <input
            style={styles.input}
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
        </label>

        <label style={styles.label}>
          Shift Type
          <select
            style={styles.input}
            value={shiftType}
            onChange={(e) => setShiftType(e.target.value)}
          >
            <option value="full">Full</option>
            <option value="morning">Morning</option>
            <option value="afternoon">Afternoon</option>
          </select>
        </label>

        <label style={styles.label}>
          Leave Type
          <select
            style={styles.input}
            value={leaveType}
            onChange={(e) => setLeaveType(e.target.value)}
          >
            <option value="">None (Work)</option>
            <option value="paid">Paid Leave</option>
            <option value="holiday">Holiday</option>
            <option value="sick">Sick</option>
            <option value="other">Other</option>
          </select>
        </label>

        <label style={styles.label}>
          Note
          <input
            style={{ ...styles.input, minWidth: 180 }}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Optional"
          />
        </label>
      </div>

      <div style={styles.actions}>
        <button type="submit" style={styles.saveBtn} disabled={saving}>
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button type="button" style={styles.cancelBtn} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
};

const styles: Record<string, React.CSSProperties> = {
  form: {
    padding: 16,
    background: '#fff',
    border: '1px solid #dee2e6',
    borderRadius: 6,
    marginBottom: 12,
  },
  title: { fontWeight: 600, fontSize: 14, marginBottom: 12 },
  error: {
    background: '#f8d7da',
    color: '#721c24',
    padding: '8px 12px',
    borderRadius: 4,
    fontSize: 13,
    marginBottom: 12,
    whiteSpace: 'pre-line',
  },
  row: { display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 },
  label: { display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13, fontWeight: 500 },
  input: {
    padding: '6px 10px',
    border: '1px solid #ced4da',
    borderRadius: 4,
    fontSize: 13,
    minWidth: 120,
  },
  actions: { display: 'flex', gap: 8 },
  saveBtn: {
    padding: '6px 16px',
    background: '#0d6efd',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    fontSize: 13,
    cursor: 'pointer',
  },
  cancelBtn: {
    padding: '6px 16px',
    background: '#e2e3e5',
    color: '#383d41',
    border: 'none',
    borderRadius: 4,
    fontSize: 13,
    cursor: 'pointer',
  },
};

export default ShiftForm;
