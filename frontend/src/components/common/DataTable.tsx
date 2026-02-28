import React from 'react';

interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  emptyMessage?: string;
}

function DataTable<T extends { id: number }>({
  columns,
  data,
  loading,
  emptyMessage = 'No data',
}: DataTableProps<T>) {
  if (loading) {
    return <div style={styles.loading}>Loading...</div>;
  }

  return (
    <div style={styles.wrapper}>
      <table style={styles.table}>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} style={styles.th}>{col.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} style={styles.empty}>
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((item) => (
              <tr key={item.id} style={styles.tr}>
                {columns.map((col) => (
                  <td key={col.key} style={styles.td}>
                    {col.render
                      ? col.render(item)
                      : String((item as any)[col.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: { overflowX: 'auto' },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    background: '#fff',
    borderRadius: 8,
    overflow: 'hidden',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  th: {
    textAlign: 'left',
    padding: '12px 16px',
    background: '#f8f9fa',
    borderBottom: '2px solid #dee2e6',
    fontSize: 13,
    fontWeight: 600,
    color: '#495057',
  },
  td: {
    padding: '10px 16px',
    borderBottom: '1px solid #eee',
    fontSize: 14,
  },
  tr: {},
  empty: {
    textAlign: 'center',
    padding: 24,
    color: '#999',
  },
  loading: {
    textAlign: 'center',
    padding: 24,
    color: '#888',
  },
};

export default DataTable;
