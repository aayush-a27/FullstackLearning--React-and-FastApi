import { useNavigate, useLocation } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { User, Settings, LogOut } from 'lucide-react';
import { ROUTES } from '../../utils/constants';
import { useAuth } from '../../hooks/useAuth';
import ModelSelector from './ModelSelector';
import Avatar from '../common/Avatar';

export default function LeftSidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  const navItems = [
    { icon: User, label: 'Profile', path: ROUTES.PROFILE },
    { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS },
  ];

  return (
    <div className="h-full w-72 glass border-r border-glass-border flex flex-col">
      {/* User info */}
      <div className="p-4 border-b border-glass-border">
        <div className="flex items-center gap-3">
          <Avatar name={user?.full_name || user?.username} src={user?.avatar_url} size="md" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-text-primary truncate">
              {user?.full_name || user?.username || 'User'}
            </p>
            <p className="text-xs text-text-muted truncate">{user?.email || ''}</p>
          </div>
        </div>
      </div>

      {/* Model Selection */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <ModelSelector />
      </div>

      {/* Bottom Navigation */}
      <div className="p-3 border-t border-glass-border space-y-1">
        {navItems.map(({ icon: Icon, label, path }) => (
          <button
            key={path}
            id={`nav-${label.toLowerCase()}`}
            onClick={() => navigate(path)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 ${
              location.pathname === path
                ? 'bg-primary-500/15 text-primary-400 font-medium'
                : 'text-text-secondary hover:bg-primary-500/8 hover:text-text-primary'
            }`}
          >
            <Icon size={18} />
            {label}
          </button>
        ))}
        <button
          id="nav-logout"
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-text-secondary hover:bg-danger/10 hover:text-danger transition-all duration-200"
        >
          <LogOut size={18} />
          Logout
        </button>
      </div>
    </div>
  );
}
