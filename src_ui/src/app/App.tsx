import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AuthGuard from './AuthGuard';
import AppLayout from './AppLayout';
import LoginPage from '../features/auth/LoginPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/app"
          element={
            <AuthGuard>
              <AppLayout />
            </AuthGuard>
          }
        />
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
