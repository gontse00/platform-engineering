import type { ChatMessage } from '../types'

type MessageListProps = {
  messages: ChatMessage[]
}

export function MessageList({ messages }: MessageListProps) {
  return (
    <div className="message-list">
      {messages.map((message) => (
        <article key={message.id} className={`message-bubble ${message.role}`}>
          <div className="message-role">{message.role === 'assistant' ? 'Support guide' : message.role === 'system' ? 'System' : 'You'}</div>
          <p>{message.content}</p>
        </article>
      ))}
    </div>
  )
}
