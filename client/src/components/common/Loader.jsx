export default function Loader({ size = 'md', text = '' }) {
  const sizes = {
    sm: 'w-5 h-5 border-2',
    md: 'w-8 h-8 border-[3px]',
    lg: 'w-12 h-12 border-4',
  };

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div
        className={`${sizes[size]} border-primary-500/20 border-t-primary-500 rounded-full animate-spin`}
      />
      {text && <p className="text-sm text-text-muted animate-pulse">{text}</p>}
    </div>
  );
}
