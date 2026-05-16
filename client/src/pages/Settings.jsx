import { useSelector, useDispatch } from 'react-redux';
import { Monitor, Bell, Shield, Trash2 } from 'lucide-react';
import { setSmartSwitch } from '../features/model/modelSlice';
import Navbar from '../components/layout/Navbar';
import Button from '../components/common/Button';

export default function Settings() {
  const dispatch = useDispatch();
  const { smartSwitchEnabled } = useSelector((state) => state.model);

  const settingSections = [
    {
      title: 'Appearance',
      icon: Monitor,
      items: [
        {
          label: 'Theme',
          description: 'Dark theme is active (default)',
          type: 'text',
          value: 'Dark Green',
        },
      ],
    },
    {
      title: 'AI Preferences',
      icon: Shield,
      items: [
        {
          label: 'Smart Model Switch',
          description:
            'Automatically switch AI model based on question complexity and API availability',
          type: 'toggle',
          value: smartSwitchEnabled,
          onChange: () => dispatch(setSmartSwitch(!smartSwitchEnabled)),
        },
      ],
    },
    {
      title: 'Notifications',
      icon: Bell,
      items: [
        {
          label: 'Email Notifications',
          description: 'Receive updates about new features',
          type: 'toggle',
          value: false,
          onChange: () => {},
        },
      ],
    },
  ];

  return (
    <div className="flex flex-col h-full">
      <Navbar />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-lg mx-auto animate-slide-up">
          <h1 className="text-2xl font-bold text-text-primary mb-6">Settings</h1>

          <div className="space-y-6">
            {settingSections.map((section) => {
              const SectionIcon = section.icon;
              return (
                <div key={section.title} className="glass rounded-xl border border-glass-border overflow-hidden">
                  <div className="flex items-center gap-2 px-5 py-3 border-b border-glass-border">
                    <SectionIcon size={16} className="text-primary-400" />
                    <h2 className="text-sm font-semibold text-text-primary">
                      {section.title}
                    </h2>
                  </div>
                  <div className="divide-y divide-glass-border">
                    {section.items.map((item) => (
                      <div
                        key={item.label}
                        className="flex items-center justify-between px-5 py-4"
                      >
                        <div>
                          <p className="text-sm text-text-primary">{item.label}</p>
                          <p className="text-xs text-text-muted mt-0.5">
                            {item.description}
                          </p>
                        </div>
                        {item.type === 'toggle' ? (
                          <button
                            onClick={item.onChange}
                            className={`relative w-10 h-5.5 rounded-full transition-colors duration-200 ${
                              item.value ? 'bg-primary-600' : 'bg-surface-600'
                            }`}
                          >
                            <div
                              className={`absolute top-0.5 w-4.5 h-4.5 rounded-full bg-white shadow-sm transition-transform duration-200 ${
                                item.value ? 'translate-x-5' : 'translate-x-0.5'
                              }`}
                            />
                          </button>
                        ) : (
                          <span className="text-sm text-text-muted">{item.value}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}

            {/* Danger zone */}
            <div className="glass rounded-xl border border-danger/20 overflow-hidden">
              <div className="flex items-center gap-2 px-5 py-3 border-b border-danger/20">
                <Trash2 size={16} className="text-danger" />
                <h2 className="text-sm font-semibold text-danger">Danger Zone</h2>
              </div>
              <div className="px-5 py-4">
                <p className="text-sm text-text-secondary mb-3">
                  Permanently delete your account and all associated data.
                </p>
                <Button variant="danger" size="sm">
                  Delete Account
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
