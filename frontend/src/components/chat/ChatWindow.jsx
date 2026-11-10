import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

import { getConversation } from "../../features/chat/chatApi";
import { useWorkspace } from "../../context/WorkspaceContext";
import { Button } from "../ui/Button";
import { ChatInput } from "./ChatInput";
import { ChatMessage } from "./ChatMessage";

export function ChatWindow({ repositoryId, conversationId, setConversationId }) {
  const { selectCitation, activeCitation, clearSelection } = useWorkspace();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const controllerRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      setLoading(false);
      setError(null);
      return;
    }
    loadConversation(conversationId);
  }, [conversationId, repositoryId]);

  async function loadConversation(id) {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError(null);
    try {
      const data = await getConversation(id, repositoryId, controller.signal);
      setMessages(data.messages || []);
    } catch (err) {
      if (err?.cancelled) return;
      setError(err.message || "Could not load conversation history.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  function handleCitationClick(citation) {
    selectCitation(citation);
    clearSelection();
  }

  if (loading) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-[12px] text-muted">
        <Loader2 size={16} className="animate-spin mr-2" aria-hidden="true" />
        Loading conversation…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center text-[12px] text-danger">
        <AlertTriangle size={20} className="mb-2" aria-hidden="true" />
        {error}
        <Button variant="secondary" className="mt-3" onClick={() => setLoading(true) && loadConversation(conversationId ?? "")}>
          Try again
        </Button>
      </div>
    );
  }

  if (!conversationId) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center text-[12px] text-muted/80">
        <p>Start a conversation by asking a question.</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col min-h-[300px]">
      <div className="overflow-y-auto flex-1 p-4 scroll-smooth" ref={scrollRef}>
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            onCitationClick={handleCitationClick}
          />
        ))}
        {messages.length === 0 && (
          <div className="text-center text-[12px] text-muted/80 mt-10">
            No messages yet. Ask a question to get started.
          </div>
        )}
      </div>

      <ChatInput
        repositoryId={repositoryId}
        conversationId={conversationId}
        setConversationId={setConversationId}
      />
    </div>
  );
}
