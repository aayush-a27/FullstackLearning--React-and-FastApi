import { Outlet } from 'react-router-dom';
import { useSelector } from 'react-redux';
import LeftSidebar from '../sidebar/LeftSidebar';
import RightSidebar from '../sidebar/RightSidebar';

export default function AppLayout() {
  const { leftSidebarOpen, rightSidebarOpen } = useSelector((state) => state.ui);

  return (
    <div className="h-screen flex bg-radial-gradient overflow-hidden">
      {/* Ambient background effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary-500/8 rounded-full blur-3xl" />
      </div>

      {/* Left Sidebar — Model Selection + Profile + Settings */}
      <aside
        className={`relative z-20 h-full transition-all duration-300 ease-in-out ${
          leftSidebarOpen ? 'w-72' : 'w-0'
        } overflow-hidden flex-shrink-0`}
      >
        <LeftSidebar />
      </aside>

      {/* Main Content — Chat Area */}
      <main className="relative z-10 flex-1 flex flex-col min-w-0">
        <Outlet />
      </main>

      {/* Right Sidebar — Chat History */}
      <aside
        className={`relative z-20 h-full transition-all duration-300 ease-in-out ${
          rightSidebarOpen ? 'w-72' : 'w-0'
        } overflow-hidden flex-shrink-0`}
      >
        <RightSidebar />
      </aside>
    </div>
  );
}
