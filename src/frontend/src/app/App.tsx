import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AuthGuard from './AuthGuard';
import AppLayout from './AppLayout';
import LoginPage from '../features/auth/LoginPage';
import CompletePage from '../features/complete/CompletePage';
import WelcomePage from '../features/welcome/WelcomePage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/welcome"
          element={
            <AuthGuard>
              <WelcomePage />
            </AuthGuard>
          }
        />
        <Route
          path="/app"
          element={
            <AuthGuard>
              <AppLayout />
            </AuthGuard>
          }
        />
        <Route
          path="/complete"
          element={
            <AuthGuard>
              <CompletePage />
            </AuthGuard>
          }
        />
        <Route path="*" element={<Navigate to="/welcome" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
