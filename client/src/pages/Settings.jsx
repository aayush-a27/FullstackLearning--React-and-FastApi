import { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import toast from 'react-hot-toast';
import { Monitor, Bell, Shield, Trash2, AlertTriangle } from 'lucide-react';
import { setSmartSwitch } from '../features/model/modelSlice';
import { useAuth } from '../hooks/useAuth';
import { getFriendlyError } from '../utils/helpers';
import Button from '../components/common/Button';
import Input from '../components/common/Input';

function Toggle({ checked, onChange, disabled, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={onChange}
      className={`relative w-10 h-5.5 rounded-full transition-colors duration-200 flex-shrink-0 disabled:opacity-50 ${
        checked ? 'bg-primary-600' : 'bg-surface-600'
      }`}
    >
      <div
        className={`absolute top-0.5 w-4.5 h-4.5 rounded-full bg-white shadow-sm transition-transform duration-200 ${
          checked ? 'translate-x-5' : 'translate-x-0.5'
        }`}
      />
    </button>
  );
}

function Section({ icon: Icon, title, children }) {
  return (
    <div className="glass rounded-xl border border-glass-border overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-glass-border">
        <Icon size={16} className="text-primary-400" />
        <h2 className="text-sm font-semibold text-text-primary">{title}</h2>
      </div>
      <div className="divide-y divide-glass-border">{children}</div>
    </div>
  );
}

function Row({ label, description, children }) {
  return (
    <div className="flex items-center justify-between gap-4 px-5 py-4">
      <div className="min-w-0">
        <p className="text-sm text-text-primary">{label}</p>
        <p className="text-xs text-text-muted mt-0.5">{description}</p>
      </div>
      {children}
    </div>
  );
}

export default function Settings() {
  const dispatch = useDispatch();
  const { smartSwitchEnabled } = useSelector((state) => state.model);
  const { user, saveProfile, deleteAccount } = useAuth();

  const [savingNotifications, setSavingNotifications] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [password, setPassword] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  const emailNotifications = user?.email_notifications ?? false;

  const handleNotificationsToggle = async () => {
    setSavingNotifications(true);
    try {
      await saveProfile({ email_notifications: !emailNotifications });
      toast.success(emailNotifications ? 'Email updates turned off' : 'Email updates turned on');
    } catch (err) {
      toast.error(getFriendlyError(err, "Couldn't save that setting. Please try again."));
    }
    setSavingNotifications(false);
  };

  const handleDelete = async (e) => {
    e.preventDefault();
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteAccount(password);
      toast.success('Your account has been deleted.');
    } catch (err) {
      setDeleteError(
        getFriendlyError(err, "Couldn't delete your account. Please try again.")
      );
      setDeleting(false);
    }
  };

  return (
    // Rendered inside the modal frame in AppLayout, which supplies the border and close button
    <div className="p-6 sm:p-8">
      <h1 className="text-2xl font-bold text-text-primary mb-6 pr-10">Settings</h1>

      <div className="space-y-6">
        <Section icon={Monitor} title="Appearance">
          <Row label="Theme" description="Dark theme is active (default)">
            <span className="text-sm text-text-muted">Dark Green</span>
          </Row>
        </Section>

        <Section icon={Shield} title="AI Preferences">
          <Row
            label="Smart Model Switch"
            description="Pick the AI model automatically based on how complex your question is"
          >
            <Toggle
              label="Smart Model Switch"
              checked={smartSwitchEnabled}
              onChange={() => dispatch(setSmartSwitch(!smartSwitchEnabled))}
            />
          </Row>
        </Section>

        <Section icon={Bell} title="Notifications">
          <Row
            label="Email Notifications"
            description="Receive updates about new features. Saved to your account; no emails are sent yet."
          >
            <Toggle
              label="Email Notifications"
              checked={emailNotifications}
              disabled={savingNotifications}
              onChange={handleNotificationsToggle}
            />
          </Row>
        </Section>

        {/* Danger zone */}
        <div className="glass rounded-xl border border-danger/20 overflow-hidden">
          <div className="flex items-center gap-2 px-5 py-3 border-b border-danger/20">
            <Trash2 size={16} className="text-danger" />
            <h2 className="text-sm font-semibold text-danger">Danger Zone</h2>
          </div>
          <div className="px-5 py-4">
            {!confirmingDelete ? (
              <>
                <p className="text-sm text-text-secondary mb-3">
                  Permanently delete your account and all associated data.
                </p>
                <Button variant="danger" size="sm" onClick={() => setConfirmingDelete(true)}>
                  Delete Account
                </Button>
              </>
            ) : (
              <form onSubmit={handleDelete} className="space-y-3">
                <div className="flex gap-2 text-xs text-danger bg-danger/10 px-3 py-2 rounded-lg">
                  <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
                  <span>
                    This deletes your account, every chat and all uploaded PDFs.
                    It cannot be undone.
                  </span>
                </div>
                <Input
                  id="delete-account-password"
                  label="Enter your password to confirm"
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setDeleteError(null);
                  }}
                  autoComplete="current-password"
                />
                {deleteError && (
                  <p className="text-xs text-danger bg-danger/10 px-3 py-2 rounded-lg">
                    {deleteError}
                  </p>
                )}
                <div className="flex gap-2">
                  <Button
                    type="submit"
                    variant="danger"
                    size="sm"
                    loading={deleting}
                    disabled={!password}
                  >
                    Delete my account
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setConfirmingDelete(false);
                      setPassword('');
                      setDeleteError(null);
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
