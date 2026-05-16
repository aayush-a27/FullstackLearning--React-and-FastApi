import ChatArea from '../components/chat/ChatArea';
import ChatInput from '../components/chat/ChatInput';

export default function Dashboard() {
  return (
    <div className="flex flex-col h-full">
      <ChatArea />
      <ChatInput />
    </div>
  );
}
