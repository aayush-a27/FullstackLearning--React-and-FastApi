import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { ChevronDown, User, Settings, LogOut, Cpu } from 'lucide-react';
import { ROUTES } from '../../utils/constants';
import { useAuth } from '../../hooks/useAuth';
import Avatar from '../common/Avatar';
import ModelSelector from '../sidebar/ModelSelector';

export default function TopBarDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const [showModels, setShowModels] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { selectedModel } = useSelector((state) => state.model);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
        setShowModels(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
        setShowModels(false);
      }
    };
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, []);

  const handleNavigate = (path) => {
    navigate(path);
    setIsOpen(false);
  };

  const handleLogout = () => {
    setIsOpen(false);
    logout();
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger button */}
      <button
        id="topbar-dropdown-trigger"
        onClick={() => {
          setIsOpen(!isOpen);
          setShowModels(false);
        }}
        className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl hover:bg-primary-500/10 transition-all duration-200"
      >
        <Avatar name={user?.full_name || user?.username} size="sm" />
        <div className="hidden sm:flex flex-col items-start min-w-0">
          <span className="text-xs font-medium text-text-primary truncate max-w-[100px]">
            {user?.full_name || user?.username || 'User'}
          </span>
          <span className="text-[10px] text-text-muted truncate max-w-[100px]">
            {selectedModel?.name}
          </span>
        </div>
        <ChevronDown
          size={14}
          className={`text-text-muted transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div
          className="dropdown-menu absolute right-0 top-full mt-2 w-72 z-50"
          id="topbar-dropdown-menu"
        >
          {/* User info */}
          <div className="px-4 py-3 border-b border-glass-border">
            <div className="flex items-center gap-3">
              <Avatar name={user?.full_name || user?.username} size="md" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-text-primary truncate">
                  {user?.full_name || user?.username || 'User'}
                </p>
                <p className="text-xs text-text-muted truncate">
                  {user?.email || ''}
                </p>
              </div>
            </div>
          </div>

          {/* Model Selection */}
          <div className="px-2 py-1">
            <button
              className="dropdown-item w-full"
              onClick={() => setShowModels(!showModels)}
            >
              <Cpu size={16} />
              <span className="flex-1 text-left">AI Model</span>
              <span className="text-xs text-primary-400 flex items-center gap-1">
                {selectedModel?.icon} {selectedModel?.name}
              </span>
              <ChevronDown
                size={12}
                className={`text-text-muted transition-transform duration-200 ${
                  showModels ? 'rotate-180' : ''
                }`}
              />
            </button>
            {showModels && (
              <div className="px-2 pb-2 animate-fade-in">
                <ModelSelector compact onSelect={() => setShowModels(false)} />
              </div>
            )}
          </div>

          <div className="dropdown-divider" />

          {/* Navigation */}
          <div className="px-2 py-1">
            <button
              className={`dropdown-item ${
                location.pathname === ROUTES.PROFILE ? 'text-primary-400' : ''
              }`}
              onClick={() => handleNavigate(ROUTES.PROFILE)}
            >
              <User size={16} />
              Profile
            </button>
            <button
              className={`dropdown-item ${
                location.pathname === ROUTES.SETTINGS ? 'text-primary-400' : ''
              }`}
              onClick={() => handleNavigate(ROUTES.SETTINGS)}
            >
              <Settings size={16} />
              Settings
            </button>
          </div>

          <div className="dropdown-divider" />

          {/* Logout */}
          <div className="px-2 py-1">
            <button
              className="dropdown-item danger"
              onClick={handleLogout}
              id="dropdown-logout"
            >
              <LogOut size={16} />
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
