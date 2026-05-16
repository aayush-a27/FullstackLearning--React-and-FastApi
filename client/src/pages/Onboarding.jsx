import { useState } from 'react';
import { Globe, Target, Calendar, ArrowRight, ArrowLeft, Check } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import Button from '../components/common/Button';
import { LANGUAGES, PURPOSES } from '../utils/constants';

export default function Onboarding() {
  const { submitOnboarding, isLoading } = useAuth();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    language: '',
    purpose: '',
    date_of_birth: '',
  });

  const steps = [
    {
      title: 'Choose your language',
      subtitle: 'Select your preferred language for AI responses',
      icon: Globe,
    },
    {
      title: 'What brings you here?',
      subtitle: 'Help us personalize your experience',
      icon: Target,
    },
    {
      title: 'Date of Birth',
      subtitle: 'For a personalized experience',
      icon: Calendar,
    },
  ];

  const canProceed = () => {
    if (step === 0) return !!form.language;
    if (step === 1) return !!form.purpose;
    if (step === 2) return !!form.date_of_birth;
    return false;
  };

  const handleNext = () => {
    if (step < 2) setStep(step + 1);
    else submitOnboarding(form);
  };

  const CurrentIcon = steps[step].icon;

  return (
    <div className="min-h-screen bg-radial-gradient flex items-center justify-center p-4">
      {/* Ambient effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/3 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl animate-pulse-glow" />
      </div>

      <div className="relative z-10 w-full max-w-lg animate-slide-up">
        <div className="glass rounded-2xl p-8 shadow-2xl shadow-primary-900/20">
          {/* Progress bar */}
          <div className="flex gap-2 mb-8">
            {steps.map((_, i) => (
              <div
                key={i}
                className={`flex-1 h-1 rounded-full transition-colors duration-300 ${
                  i <= step ? 'bg-primary-500' : 'bg-surface-600'
                }`}
              />
            ))}
          </div>

          {/* Step header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-primary-500/20 border border-primary-500/30 mb-4">
              <CurrentIcon size={28} className="text-primary-400" />
            </div>
            <h2 className="text-xl font-bold text-text-primary">{steps[step].title}</h2>
            <p className="text-sm text-text-muted mt-1">{steps[step].subtitle}</p>
          </div>

          {/* Step content */}
          <div className="min-h-[200px]">
            {/* Step 0: Language */}
            {step === 0 && (
              <div className="grid grid-cols-2 gap-2 animate-fade-in">
                {LANGUAGES.map((lang) => (
                  <button
                    key={lang}
                    onClick={() => setForm({ ...form, language: lang })}
                    className={`px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                      form.language === lang
                        ? 'bg-primary-600 text-white border border-primary-500'
                        : 'bg-surface-700 text-text-secondary border border-glass-border hover:border-primary-500/30 hover:bg-surface-600'
                    }`}
                  >
                    {lang}
                  </button>
                ))}
              </div>
            )}

            {/* Step 1: Purpose */}
            {step === 1 && (
              <div className="grid grid-cols-2 gap-3 animate-fade-in">
                {PURPOSES.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setForm({ ...form, purpose: p.id })}
                    className={`flex flex-col items-center gap-2 px-4 py-4 rounded-xl text-sm transition-all duration-200 ${
                      form.purpose === p.id
                        ? 'bg-primary-600 text-white border border-primary-500'
                        : 'bg-surface-700 text-text-secondary border border-glass-border hover:border-primary-500/30 hover:bg-surface-600'
                    }`}
                  >
                    <span className="text-2xl">{p.icon}</span>
                    <span className="font-medium text-center">{p.label}</span>
                  </button>
                ))}
              </div>
            )}

            {/* Step 2: DOB */}
            {step === 2 && (
              <div className="flex flex-col items-center gap-4 animate-fade-in">
                <input
                  id="onboarding-dob"
                  type="date"
                  value={form.date_of_birth}
                  onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
                  className="w-full max-w-xs bg-surface-800 border border-glass-border rounded-xl px-4 py-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all [color-scheme:dark]"
                />
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8">
            <Button
              variant="ghost"
              onClick={() => setStep(step - 1)}
              disabled={step === 0}
              className={step === 0 ? 'invisible' : ''}
            >
              <ArrowLeft size={16} />
              Back
            </Button>
            <Button
              onClick={handleNext}
              disabled={!canProceed()}
              loading={isLoading && step === 2}
            >
              {step === 2 ? (
                <>
                  Get Started
                  <Check size={16} />
                </>
              ) : (
                <>
                  Continue
                  <ArrowRight size={16} />
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
