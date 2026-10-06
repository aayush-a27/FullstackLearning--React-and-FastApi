import { useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { setSelectedModel, toggleSmartSwitch, setModelHealth } from '../../features/model/modelSlice';
import { Zap } from 'lucide-react';
import axiosInstance from '../../api/axiosInstance';
import { MODELS } from '../../api/endpoints';

const HEALTH_LABELS = {
  healthy: 'Available',
  degraded: 'Busy — recent requests failed, other models will be used as backup',
  down: 'Unavailable',
};

export default function ModelSelector({ compact = false, onSelect }) {
  const dispatch = useDispatch();
  const { selectedModel, smartSwitchEnabled, availableModels, modelHealth } = useSelector(
    (state) => state.model
  );

  // Refresh provider health whenever the selector is shown (server caches the checks)
  useEffect(() => {
    axiosInstance
      .get(MODELS.HEALTH)
      .then(({ data }) => dispatch(setModelHealth(data)))
      .catch(() => {}); // keep the last known status
  }, [dispatch]);

  const getHealthColor = (provider) => {
    const status = modelHealth[provider];
    if (status === 'down') return 'bg-danger';
    if (status === 'degraded') return 'bg-warning';
    if (status === 'healthy') return 'bg-primary-500';
    return 'bg-text-muted/50'; // not checked yet
  };

  const handleSelect = (modelId) => {
    dispatch(setSelectedModel(modelId));
    if (onSelect) onSelect();
  };

  return (
    <div className="space-y-2">
      {/* Model list (always visible, no dropdown toggle in compact) */}
      <div className={`space-y-0.5 ${compact ? '' : 'space-y-1'}`}>
        {availableModels.map((model) => (
          <button
            key={model.id}
            onClick={() => handleSelect(model.id)}
            className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition-all duration-150 ${
              model.id === selectedModel?.id
                ? 'bg-primary-500/15 text-primary-400 border border-primary-500/20'
                : 'hover:bg-surface-600 text-text-secondary hover:text-text-primary border border-transparent'
            } ${compact ? 'text-xs py-1.5 px-2' : 'text-sm'}`}
          >
            <span className={compact ? 'text-sm' : 'text-lg'}>{model.icon}</span>
            <div className="flex-1 min-w-0">
              <p className={`font-medium truncate ${compact ? 'text-xs' : 'text-sm'}`}>
                {model.name}
              </p>
              {!compact && (
                <p className="text-xs text-text-muted truncate">{model.description}</p>
              )}
            </div>
            <div
              className={`w-2 h-2 rounded-full flex-shrink-0 ${getHealthColor(model.provider)}`}
              title={HEALTH_LABELS[modelHealth[model.provider]] || 'Checking…'}
            />
          </button>
        ))}
      </div>

      {/* Smart Switch Toggle */}
      <div className="flex items-center justify-between px-1 pt-1">
        <div className="flex items-center gap-2">
          <Zap size={compact ? 12 : 14} className="text-warning" />
          <span className={`text-text-secondary ${compact ? 'text-[10px]' : 'text-xs'}`}>
            Smart Switch
          </span>
        </div>
        <button
          id="smart-switch-toggle"
          onClick={() => dispatch(toggleSmartSwitch())}
          className={`relative ${compact ? 'w-7 h-4' : 'w-9 h-5'} rounded-full transition-colors duration-200 ${
            smartSwitchEnabled ? 'bg-primary-600' : 'bg-surface-600'
          }`}
        >
          <div
            className={`absolute top-0.5 ${compact ? 'w-3 h-3' : 'w-4 h-4'} rounded-full bg-white shadow-sm transition-transform duration-200 ${
              smartSwitchEnabled
                ? compact ? 'translate-x-3' : 'translate-x-4'
                : 'translate-x-0.5'
            }`}
          />
        </button>
      </div>
    </div>
  );
}
