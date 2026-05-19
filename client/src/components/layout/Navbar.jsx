import TopBarDropdown from './TopBarDropdown';

export default function Navbar() {
  return (
    <nav className="flex items-center justify-between px-4 py-2.5 glass border-b border-glass-border flex-shrink-0">
      {/* Left — Branding */}
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-primary-500/20 border border-primary-500/30 flex items-center justify-center">
          <svg
            className="w-4 h-4 text-primary-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>
        <span className="text-sm font-semibold text-text-primary">
          PDF Chat AI
        </span>
      </div>

      {/* Right — Dropdown */}
      <TopBarDropdown />
    </nav>
  );
}
