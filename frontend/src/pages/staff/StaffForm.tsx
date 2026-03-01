import React, { useEffect, useState } from 'react';
import { createStaff, fetchStores, updateStaff } from '../../api/endpoints';
import { parseApiError } from '../../api/parseApiError';
import type { Staff, Store } from '../../types/models';

interface Props {
  staff?: Staff;
  onSaved: () => void;
  onCancel: () => void;
}

const StaffForm: React.FC<Props> = ({ staff, onSaved, onCancel }) => {
  const isEdit = !!staff;

  const [name, setName] = useState(staff?.name ?? '');
  const [role, setRole] = useState<string>(staff?.role ?? 'pharmacist');
  const [employmentType, setEmploymentType] = useState<string>(
    staff?.employment_type ?? 'full_time',
  );
  const [workStatus, setWorkStatus] = useState<string>(
    staff?.work_status ?? 'active',
  );
  const [storeId, setStoreId] = useState<string>(
    staff?.store != null ? String(staff.store) : '',
  );
  const [paidLeaveDeadline, setPaidLeaveDeadline] = useState(
    staff?.paid_leave_deadline ?? '09-15',
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [stores, setStores] = useState<Store[]>([]);

  useEffect(() => {
    fetchStores({ page_size: '200', is_active: 'true' })
      .then((res) => setStores(res.data.results))
      .catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');

    const payload: Partial<Staff> = {
      name,
      role: role as Staff['role'],
      employment_type: employmentType as Staff['employment_type'],
      work_status: workStatus as Staff['work_status'],
      store: storeId ? Number(storeId) : null,
      paid_leave_deadline: paidLeaveDeadline,
    };

    try {
      if (isEdit) {
        await updateStaff(staff!.id, payload);
      } else {
        await createStaff(payload);
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
      <div style={styles.title}>{isEdit ? `Edit: ${staff!.name}` : 'Add Staff'}</div>

      {error && <div style={styles.error}>{error}</div>}

      <div style={styles.row}>
        <label style={styles.label}>
          Name
          <input
            style={styles.input}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </label>

        <label style={styles.label}>
          Role
          <select style={styles.input} value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="pharmacist">Pharmacist</option>
            <option value="clerk">Clerk</option>
            <option value="managing_pharmacist">Managing Pharmacist</option>
          </select>
        </label>

        <label style={styles.label}>
          Employment
          <select
            style={styles.input}
            value={employmentType}
            onChange={(e) => setEmploymentType(e.target.value)}
          >
            <option value="full_time">Full-time</option>
            <option value="part_time">Part-time</option>
            <option value="dispatch">Dispatch</option>
          </select>
        </label>

        <label style={styles.label}>
          Work Status
          <select
            style={styles.input}
            value={workStatus}
            onChange={(e) => setWorkStatus(e.target.value)}
          >
            <option value="active">Active</option>
            <option value="on_leave">On Leave</option>
            <option value="maternity">Maternity</option>
            <option value="temporary">Temporary</option>
          </select>
        </label>

        <label style={styles.label}>
          Store
          <select
            style={styles.input}
            value={storeId}
            onChange={(e) => setStoreId(e.target.value)}
          >
            <option value="">-- None --</option>
            {stores.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>

        <label style={styles.label}>
          PTO Deadline
          <select
            style={styles.input}
            value={paidLeaveDeadline}
            onChange={(e) => setPaidLeaveDeadline(e.target.value)}
          >
            <option value="09-15">09/15</option>
            <option value="02-15">02/15</option>
          </select>
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

export default StaffForm;
