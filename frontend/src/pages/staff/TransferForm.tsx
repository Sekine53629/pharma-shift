import React, { useEffect, useState } from 'react';
import { fetchStores, transferStaff } from '../../api/endpoints';
import { parseApiError } from '../../api/parseApiError';
import type { Staff, Store } from '../../types/models';

interface Props {
  staff: Staff;
  onTransferred: () => void;
  onCancel: () => void;
}

const TransferForm: React.FC<Props> = ({ staff, onTransferred, onCancel }) => {
  const [stores, setStores] = useState<Store[]>([]);
  const [toStore, setToStore] = useState<string>(staff.store != null ? String(staff.store) : '');
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchStores({ page_size: '200', is_active: 'true' }).then((res) => {
      setStores(res.data.results);
    });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');

    const toStoreId = toStore === '' ? null : Number(toStore);

    try {
      await transferStaff(staff.id, toStoreId, reason);
      onTransferred();
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <div style={styles.title}>Transfer: {staff.name}</div>
      <div style={styles.subtitle}>
        Current store: {staff.store_name || '(Unassigned)'}
      </div>

      {error && <div style={styles.error}>{error}</div>}

      <div style={styles.row}>
        <label style={styles.label}>
          New Store
          <select
            style={styles.input}
            value={toStore}
            onChange={(e) => setToStore(e.target.value)}
          >
            <option value="">(Unassigned)</option>
            {stores.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>

        <label style={styles.label}>
          Reason
          <input
            style={{ ...styles.input, minWidth: 240 }}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Optional"
          />
        </label>
      </div>

      <div style={styles.actions}>
        <button type="submit" style={styles.saveBtn} disabled={saving}>
          {saving ? 'Transferring...' : 'Confirm Transfer'}
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
  title: { fontWeight: 600, fontSize: 14, marginBottom: 4 },
  subtitle: { fontSize: 12, color: '#666', marginBottom: 12 },
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
    background: '#198754',
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

export default TransferForm;
