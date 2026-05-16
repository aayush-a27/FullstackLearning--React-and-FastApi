import { Link } from 'react-router-dom';
import { Home } from 'lucide-react';
import Button from '../components/common/Button';
import { ROUTES } from '../utils/constants';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-radial-gradient flex items-center justify-center p-4">
      <div className="text-center animate-slide-up">
        <h1 className="text-8xl font-bold text-primary-500/30 mb-4">404</h1>
        <h2 className="text-2xl font-bold text-text-primary mb-2">Page Not Found</h2>
        <p className="text-text-muted mb-8 max-w-sm mx-auto">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <Link to={ROUTES.DASHBOARD}>
          <Button>
            <Home size={16} />
            Back to Dashboard
          </Button>
        </Link>
      </div>
    </div>
  );
}
