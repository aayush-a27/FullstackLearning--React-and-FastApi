import { useSelector, useDispatch } from 'react-redux';
import { setSelectedModel, toggleSmartSwitch } from '../../features/model/modelSlice';
import { Zap, ChevronDown } from 'lucide-react';
import { useState } from 'react';

export default function ModelSelector() {
  const dispatch = useDispatch();
  const { selectedModel, smartSwitchEnabled, availableModels, modelHealth } = useSelector(
    (state) => state.model
  );
  const [isOpen, setIsOpen] = useState(false);

  const getHealthColor = (provider) => {
    const status = modelHealth[provider];
    if (status === 'down') return 'bg-danger';
    if (status === 'degraded') return 'bg-warning';
    return 'bg-primary-500';
  };

  return (
    <div className="space-y-3">
      {/* Section Title */}
      <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
        AI Model
      </h3>

      {/* Model Dropdown */}
      <div className="relative">
        <button
          id="model-selector-btn"
          onClick={() => setIsOpen(!isOpen)}
          className="w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl bg-surface-800 border border-glass-border hover:border-primary-500/30 transition-all duration-200 text-left"
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-lg">{selectedModel?.icon}</span>
            <div className="min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">
                {selectedModel?.name}
              </p>
              <p className="text-xs text-text-muted truncate">{selectedModel?.provider}</p>
            </div>
          </div>
          <ChevronDown
            size={16}
            className={`text-text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          />
        </button>

        {/* Dropdown */}
        {isOpen && (
          <div className="absolute top-full left-0 right-0 mt-1 glass rounded-xl border border-glass-border shadow-2xl shadow-black/40 z-30 overflow-hidden animate-fade-in">
            {availableModels.map((model) => (
              <button
                key={model.id}
                onClick={() => {
                  dispatch(setSelectedModel(model.id));
                  setIsOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-all duration-150 ${
                  model.id === selectedModel?.id
                    ? 'bg-primary-500/15 text-primary-400'
                    : 'hover:bg-surface-600 text-text-secondary hover:text-text-primary'
                }`}
              >
                <span className="text-lg">{model.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{model.name}</p>
                  <p className="text-xs text-text-muted truncate">{model.description}</p>
                </div>
                <div className={`w-2 h-2 rounded-full ${getHealthColor(model.provider)}`} />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Smart Switch Toggle */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-warning" />
          <span className="text-xs text-text-secondary">Smart Switch</span>
        </div>
        <button
          id="smart-switch-toggle"
          onClick={() => dispatch(toggleSmartSwitch())}
          className={`relative w-9 h-5 rounded-full transition-colors duration-200 ${
            smartSwitchEnabled ? 'bg-primary-600' : 'bg-surface-600'
          }`}
        >
          <div
            className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${
              smartSwitchEnabled ? 'translate-x-4' : 'translate-x-0.5'
            }`}
          />
        </button>
      </div>
      {smartSwitchEnabled && (
        <p className="text-xs text-text-muted px-1">
          Auto-switches model based on question complexity & availability.
        </p>
      )}
    </div>
  );
}
