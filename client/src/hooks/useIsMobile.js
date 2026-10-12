import { useSyncExternalStore } from 'react';

// Below Tailwind's `md` breakpoint the three panels don't fit side by side
const MOBILE_QUERY = '(max-width: 767px)';

function subscribe(onChange) {
  const media = window.matchMedia(MOBILE_QUERY);
  media.addEventListener('change', onChange);
  return () => media.removeEventListener('change', onChange);
}

/** True on phone-sized screens; updates when the window is resized or rotated. */
export function useIsMobile() {
  return useSyncExternalStore(subscribe, () => window.matchMedia(MOBILE_QUERY).matches);
}
