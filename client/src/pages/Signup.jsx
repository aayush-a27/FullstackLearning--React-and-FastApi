import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, Lock, User, UserPlus } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { ROUTES } from '../utils/constants';

export default function Signup() {
  const { register, isLoading, error } = useAuth();
  const [form, setForm] = useState({
    username: '',
    email: '',
    fullName: '',
    password: '',
    confirmPassword: '',
  });
  const [localError, setLocalError] = useState('');

  const handleChange = (field) => (e) => {
    setForm({ ...form, [field]: e.target.value });
    setLocalError('');
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (form.password !== form.confirmPassword) {
      setLocalError('Passwords do not match');
      return;
    }
    if (form.password.length < 8) {
      setLocalError('Password must be at least 8 characters');
      return;
    }
    register(form.username, form.email, form.password, form.fullName);
  };

  const displayError = localError || error;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        id="signup-fullname"
        label="Full Name"
        placeholder="John Doe"
        value={form.fullName}
        onChange={handleChange('fullName')}
        icon={User}
        required
      />
      <Input
        id="signup-username"
        label="Username"
        placeholder="johndoe"
        value={form.username}
        onChange={handleChange('username')}
        icon={UserPlus}
        required
      />
      <Input
        id="signup-email"
        label="Email"
        type="email"
        placeholder="you@example.com"
        value={form.email}
        onChange={handleChange('email')}
        icon={Mail}
        required
      />
      <Input
        id="signup-password"
        label="Password"
        type="password"
        placeholder="Min 8 characters"
        value={form.password}
        onChange={handleChange('password')}
        icon={Lock}
        required
      />
      <Input
        id="signup-confirm-password"
        label="Confirm Password"
        type="password"
        placeholder="Re-enter password"
        value={form.confirmPassword}
        onChange={handleChange('confirmPassword')}
        icon={Lock}
        required
      />

      {displayError && (
        <div className="text-sm text-danger bg-danger/10 border border-danger/20 rounded-xl px-4 py-2.5">
          {displayError}
        </div>
      )}

      <Button
        id="signup-submit"
        type="submit"
        fullWidth
        loading={isLoading}
        disabled={!form.username || !form.email || !form.password || !form.confirmPassword}
      >
        Create Account
      </Button>

      <p className="text-center text-sm text-text-muted">
        Already have an account?{' '}
        <Link
          to={ROUTES.LOGIN}
          className="text-primary-400 hover:text-primary-300 font-medium transition-colors"
        >
          Sign in
        </Link>
      </p>
    </form>
  );
}
