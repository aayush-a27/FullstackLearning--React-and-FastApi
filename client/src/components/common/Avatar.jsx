import { getInitials } from '../../utils/helpers';

// Initials badge (profile pictures aren't supported)
export default function Avatar({ name, size = 'md', className = '' }) {
  const sizes = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-14 h-14 text-lg',
    xl: 'w-20 h-20 text-2xl',
  };

  return (
    <div
      className={`${sizes[size]} rounded-full bg-primary-600/20 border-2 border-primary-500/30 flex items-center justify-center font-semibold text-primary-400 ${className}`}
    >
      {getInitials(name)}
    </div>
  );
}
