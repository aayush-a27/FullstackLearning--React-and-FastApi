import { Routes, Route, Navigate } from 'react-router-dom';
import { ROUTES } from '../utils/constants';
import ProtectedRoute from './ProtectedRoute';
import AuthLayout from '../components/layout/AuthLayout';
import AppLayout from '../components/layout/AppLayout';
import Login from '../pages/Login';
import Signup from '../pages/Signup';
import Onboarding from '../pages/Onboarding';
import Dashboard from '../pages/Dashboard';
import Profile from '../pages/Profile';
import Settings from '../pages/Settings';
import NotFound from '../pages/NotFound';

export default function AppRoutes() {
  return (
    <Routes>
      {/* Public routes — Auth pages */}
      <Route element={<AuthLayout />}>
        <Route path={ROUTES.LOGIN} element={<Login />} />
        <Route path={ROUTES.SIGNUP} element={<Signup />} />
      </Route>

      {/* Protected routes — require authentication */}
      <Route element={<ProtectedRoute />}>
        <Route path={ROUTES.ONBOARDING} element={<Onboarding />} />
        <Route element={<AppLayout />}>
          <Route path={ROUTES.DASHBOARD} element={<Dashboard />} />
          <Route path={ROUTES.CHAT} element={<Dashboard />} />
          <Route path={ROUTES.PROFILE} element={<Profile />} />
          <Route path={ROUTES.SETTINGS} element={<Settings />} />
        </Route>
      </Route>

      {/* Redirect root to dashboard */}
      <Route path={ROUTES.HOME} element={<Navigate to={ROUTES.DASHBOARD} replace />} />

      {/* 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
