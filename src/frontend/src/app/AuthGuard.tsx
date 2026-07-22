import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useSurveys } from '../api/hooks';

export default function AuthGuard({ children }: { children: ReactNode }) {
  const { isLoading, error } = useSurveys();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-info)]" />
      </div>
    );
  }

  if (error) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
