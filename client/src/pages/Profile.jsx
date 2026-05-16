import { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { Camera, Save } from 'lucide-react';
import { updateUser } from '../features/auth/authSlice';
import Avatar from '../components/common/Avatar';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import Navbar from '../components/layout/Navbar';
import axiosInstance from '../api/axiosInstance';
import { USERS } from '../api/endpoints';

export default function Profile() {
  const dispatch = useDispatch();
  const { user } = useSelector((state) => state.auth);
  const [form, setForm] = useState({
    full_name: user?.full_name || '',
    username: user?.username || '',
    email: user?.email || '',
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleChange = (field) => (e) => {
    setForm({ ...form, [field]: e.target.value });
    setSaved(false);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await axiosInstance.patch(USERS.UPDATE_PROFILE, form);
      dispatch(updateUser(data));
      setSaved(true);
    } catch {
      // handle error
    }
    setSaving(false);
  };

  return (
    <div className="flex flex-col h-full">
      <Navbar />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-lg mx-auto animate-slide-up">
          <h1 className="text-2xl font-bold text-text-primary mb-6">Profile</h1>

          {/* Avatar */}
          <div className="flex justify-center mb-8">
            <div className="relative group">
              <Avatar name={user?.full_name} src={user?.avatar_url} size="xl" />
              <button className="absolute bottom-0 right-0 p-1.5 rounded-full bg-primary-600 border-2 border-surface-900 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                <Camera size={14} />
              </button>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSave} className="space-y-4">
            <Input
              id="profile-fullname"
              label="Full Name"
              value={form.full_name}
              onChange={handleChange('full_name')}
            />
            <Input
              id="profile-username"
              label="Username"
              value={form.username}
              onChange={handleChange('username')}
            />
            <Input
              id="profile-email"
              label="Email"
              type="email"
              value={form.email}
              onChange={handleChange('email')}
              disabled
            />

            {/* Read-only onboarding data */}
            <div className="grid grid-cols-2 gap-4 pt-2">
              <div className="bg-surface-800 rounded-xl px-4 py-3 border border-glass-border">
                <p className="text-xs text-text-muted mb-0.5">Language</p>
                <p className="text-sm text-text-primary">{user?.language || 'Not set'}</p>
              </div>
              <div className="bg-surface-800 rounded-xl px-4 py-3 border border-glass-border">
                <p className="text-xs text-text-muted mb-0.5">Purpose</p>
                <p className="text-sm text-text-primary capitalize">
                  {user?.purpose?.replace('_', ' ') || 'Not set'}
                </p>
              </div>
            </div>

            <Button
              id="profile-save"
              type="submit"
              fullWidth
              loading={saving}
            >
              <Save size={16} />
              {saved ? 'Saved!' : 'Save Changes'}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
