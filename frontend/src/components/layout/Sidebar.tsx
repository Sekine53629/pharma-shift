import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface NavItem {
  path: string;
  label: string;
  roles?: string[];
}

const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Dashboard' },
  { path: '/stores', label: 'Stores' },
  { path: '/staff', label: 'Staff' },
  { path: '/shifts', label: 'Shifts' },
  { path: '/assignments', label: 'Assignments', roles: ['admin', 'supervisor'] },
  { path: '/hr', label: 'HR System', roles: ['admin', 'supervisor', 'store_manager'] },
  { path: '/leave', label: 'Leave Requests' },
  { path: '/staffing-check', label: 'Staffing Check', roles: ['admin', 'supervisor'] },
  { path: '/buffer', label: 'Buffer Mgmt', roles: ['admin', 'supervisor', 'store_manager'] },
];

const Sidebar: React.FC = () => {
  const { user, hasAnyRole, logout } = useAuth();
  const location = useLocation();

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.roles || hasAnyRole(...item.roles),
  );

  return (
    <aside style={styles.sidebar}>
      <div style={styles.brand}>PharmaShift</div>
      <nav style={styles.nav}>
        {visibleItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            style={{
              ...styles.link,
              ...(location.pathname === item.path ? styles.active : {}),
            }}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <div style={styles.footer}>
        <div style={styles.userInfo}>{user?.email}</div>
        <div style={styles.roles}>
          {user?.roles.map((r) => (
            <span key={r} style={styles.badge}>{r}</span>
          ))}
        </div>
        <button onClick={logout} style={styles.logoutBtn}>
          Logout
        </button>
      </div>
    </aside>
  );
};

const styles: Record<string, React.CSSProperties> = {
  sidebar: {
    width: 220,
    minHeight: '100vh',
    background: '#1a1a2e',
    color: '#fff',
    display: 'flex',
    flexDirection: 'column',
    padding: '16px 0',
    flexShrink: 0,
  },
  brand: {
    fontSize: 20,
    fontWeight: 700,
    padding: '0 16px 16px',
    borderBottom: '1px solid #333',
  },
  nav: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    padding: '8px 0',
  },
  link: {
    color: '#ccc',
    textDecoration: 'none',
    padding: '10px 16px',
    fontSize: 14,
    borderLeft: '3px solid transparent',
  },
  active: {
    color: '#fff',
    background: '#16213e',
    borderLeftColor: '#0f3460',
  },
  footer: {
    padding: '16px',
    borderTop: '1px solid #333',
  },
  userInfo: {
    fontSize: 12,
    color: '#aaa',
    marginBottom: 4,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  roles: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4,
    marginBottom: 8,
  },
  badge: {
    fontSize: 10,
    background: '#0f3460',
    padding: '2px 6px',
    borderRadius: 4,
  },
  logoutBtn: {
    width: '100%',
    padding: '6px 0',
    background: 'transparent',
    color: '#e94560',
    border: '1px solid #e94560',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 13,
  },
};

export default Sidebar;
