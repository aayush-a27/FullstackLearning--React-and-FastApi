import { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { Save } from 'lucide-react';
import { updateUser } from '../features/auth/authSlice';
import Avatar from '../components/common/Avatar';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import axiosInstance from '../api/axiosInstance';
import { USERS } from '../api/endpoints';
import { getFriendlyError } from '../utils/helpers';

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
  const [saveError, setSaveError] = useState(null);

  const handleChange = (field) => (e) => {
    setForm({ ...form, [field]: e.target.value });
    setSaved(false);
    setSaveError(null);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    try {
      // Email can't be changed here, so only send the editable fields
      const { data } = await axiosInstance.patch(USERS.UPDATE_PROFILE, {
        full_name: form.full_name,
        username: form.username.trim(),
      });
      dispatch(updateUser(data));
      setSaved(true);
    } catch (err) {
      setSaveError(
        err.response?.status === 422
          ? 'Username must be at least 3 characters with no spaces.'
          : getFriendlyError(err, "Couldn't save your profile. Please try again.")
      );
    }
    setSaving(false);
  };

  return (
    // Rendered inside the modal frame in AppLayout, which supplies the border and close button
    <div className="p-6 sm:p-8">
      <h1 className="text-2xl font-bold text-text-primary mb-6 pr-10">Profile</h1>

      {/* Initials badge */}
      <div className="flex justify-center mb-8">
        <Avatar name={user?.full_name} size="xl" />
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

        {saveError && (
          <p className="text-xs text-danger bg-danger/10 px-3 py-2 rounded-lg">{saveError}</p>
        )}

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
  );
}
