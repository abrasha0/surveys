import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLogin } from '../../api/hooks';

export default function LoginPage() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const login = useLogin();
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    login.mutate(password, {
      onSuccess: () => navigate('/welcome'),
      onError: (err) => {
        if (err instanceof Error) {
          setError(err.message);
        }
      },
    });
  };

  return (
    <div className="flex items-center justify-center h-screen bg-gray-50">
      <div className="w-full max-w-sm bg-white rounded-lg shadow-md p-8">
        <h1 className="text-2xl font-bold text-center mb-1">AnkieterAI</h1>
        <p className="text-gray-500 text-center text-sm mb-6">
          System wprowadzania ankiet papierowych
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Hasło
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md
                         focus:outline-none focus:ring-2 focus:ring-[var(--color-info)]
                         focus:border-transparent"
              autoFocus
            />
          </div>

          {error && (
            <div className="text-sm text-[var(--color-error)] bg-red-50 p-2 rounded">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={login.isPending}
            className="w-full py-2 px-4 bg-[var(--color-info)] text-white
                       rounded-md hover:opacity-90 disabled:opacity-50
                       font-medium transition-opacity"
          >
            {login.isPending ? 'Logowanie...' : 'Zaloguj'}
          </button>
        </form>
      </div>
    </div>
  );
}
