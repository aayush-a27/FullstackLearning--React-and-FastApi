import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import AppRoutes from './routes/AppRoutes';
import { useAuth } from './hooks/useAuth';
import { useEffect } from 'react';

function AppInitializer({ children }) {
  const { fetchUser } = useAuth();

  useEffect(() => {
    fetchUser();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInitializer>
        <AppRoutes />
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#1a1a1a',
              color: '#f0fdf4',
              border: '1px solid rgba(16, 185, 129, 0.15)',
              borderRadius: '12px',
              fontSize: '14px',
            },
            success: {
              iconTheme: { primary: '#10b981', secondary: '#f0fdf4' },
            },
            error: {
              iconTheme: { primary: '#ef4444', secondary: '#f0fdf4' },
            },
          }}
        />
      </AppInitializer>
    </BrowserRouter>
  );
}
