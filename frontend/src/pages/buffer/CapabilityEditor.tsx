import React, { useState } from 'react';
import { updateRounderCapabilities } from '../../api/endpoints';
import type { Staff } from '../../types/models';

interface Props {
  staff: Staff;
  onUpdated: () => void;
}

const CapabilityEditor: React.FC<Props> = ({ staff, onUpdated }) => {
  const rp = staff.rounder_profile;
  const [saving, setSaving] = useState(false);
  const [canWorkAlone, setCanWorkAlone] = useState(rp?.can_work_alone ?? false);
  const [hasCar, setHasCar] = useState(rp?.has_car ?? false);
  const [canLongDistance, setCanLongDistance] = useState(rp?.can_long_distance ?? false);
  const [maxPrescriptions, setMaxPrescriptions] = useState(rp?.max_prescriptions ?? 30);

  if (!rp) return <div style={{ color: '#999', fontSize: 13 }}>No rounder profile</div>;

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateRounderCapabilities(staff.id, {
        can_work_alone: canWorkAlone,
        has_car: hasCar,
        can_long_distance: canLongDistance,
        max_prescriptions: maxPrescriptions,
      });
      onUpdated();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.row}>
        <label style={styles.label}>
          <input
            type="checkbox"
            checked={canWorkAlone}
            onChange={(e) => setCanWorkAlone(e.target.checked)}
          />{' '}
          Solo pharmacist OK
        </label>
        <label style={styles.label}>
          <input
            type="checkbox"
            checked={hasCar}
            onChange={(e) => setHasCar(e.target.checked)}
          />{' '}
          Has car
        </label>
        <label style={styles.label}>
          <input
            type="checkbox"
            checked={canLongDistance}
            onChange={(e) => setCanLongDistance(e.target.checked)}
          />{' '}
          Long distance OK
        </label>
        <label style={styles.label}>
          Max Rx/day:{' '}
          <input
            type="number"
            value={maxPrescriptions}
            onChange={(e) => setMaxPrescriptions(Number(e.target.value))}
            style={styles.numInput}
            min={1}
            max={50}
          />
        </label>
      </div>
      <div style={styles.row}>
        <span style={{ fontSize: 13, color: '#666' }}>
          HR: {rp.hunter_rank}
        </span>
        <button onClick={handleSave} disabled={saving} style={styles.saveBtn}>
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '8px 16px',
    background: '#f8f9fa',
    borderRadius: 6,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    flexWrap: 'wrap',
  },
  label: {
    fontSize: 13,
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  numInput: {
    width: 60,
    padding: '2px 6px',
    border: '1px solid #ccc',
    borderRadius: 4,
    fontSize: 13,
  },
  saveBtn: {
    padding: '4px 16px',
    background: '#0f3460',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    fontSize: 13,
    cursor: 'pointer',
    marginLeft: 'auto',
  },
};

export default CapabilityEditor;
