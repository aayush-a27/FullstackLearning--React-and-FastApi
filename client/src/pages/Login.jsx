import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, Lock } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { ROUTES } from '../utils/constants';

export default function Login() {
  const { login, isLoading, error } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    login(email, password);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <Input
        id="login-email"
        label="Email"
        type="email"
        placeholder="you@example.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        icon={Mail}
        required
      />
      <Input
        id="login-password"
        label="Password"
        type="password"
        placeholder="Enter your password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        icon={Lock}
        required
      />

      {error && (
        <div className="text-sm text-danger bg-danger/10 border border-danger/20 rounded-xl px-4 py-2.5">
          {error}
        </div>
      )}

      <Button
        id="login-submit"
        type="submit"
        fullWidth
        loading={isLoading}
        disabled={!email || !password}
      >
        Sign In
      </Button>

      <p className="text-center text-sm text-text-muted">
        Don't have an account?{' '}
        <Link
          to={ROUTES.SIGNUP}
          className="text-primary-400 hover:text-primary-300 font-medium transition-colors"
        >
          Sign up
        </Link>
      </p>
    </form>
  );
}
