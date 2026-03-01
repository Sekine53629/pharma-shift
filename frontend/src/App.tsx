import React from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import { AuthProvider } from './contexts/AuthContext';
import LoginPage from './pages/auth/LoginPage';
import AssignmentsPage from './pages/assignments/AssignmentsPage';
import { BufferPage } from './pages/buffer';
import DashboardPage from './pages/dashboard/DashboardPage';
import HrPage from './pages/hr/HrPage';
import LeavePage from './pages/leave/LeavePage';
import ShiftsPage from './pages/shifts/ShiftsPage';
import StaffPage from './pages/staff/StaffPage';
import { StaffingCheckPage } from './pages/staffing-check';
import StoresPage from './pages/stores/StoresPage';

const App: React.FC = () => (
  <AuthProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/stores" element={<StoresPage />} />
          <Route path="/staff" element={<StaffPage />} />
          <Route path="/shifts" element={<ShiftsPage />} />
          <Route path="/assignments" element={<AssignmentsPage />} />
          <Route path="/hr" element={<HrPage />} />
          <Route path="/leave" element={<LeavePage />} />
          <Route path="/staffing-check" element={<StaffingCheckPage />} />
          <Route path="/buffer" element={<BufferPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </AuthProvider>
);

export default App;
