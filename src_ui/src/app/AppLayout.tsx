import { useNavigate } from 'react-router-dom';

export default function AppLayout() {
  const navigate = useNavigate();

  const handleLogout = async () => {
    await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include',
    });
    navigate('/login');
  };

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white">
        <span className="font-bold text-lg">AnkieterAI</span>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Wyloguj
        </button>
      </header>
      <main className="flex-1 flex items-center justify-center bg-gray-50 text-gray-400">
        Panel weryfikacji — Etap 6+
      </main>
    </div>
  );
}
