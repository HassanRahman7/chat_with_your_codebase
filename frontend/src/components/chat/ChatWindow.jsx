import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

import { getConversation } from "../../features/chat/chatApi";
import { useWorkspace } from "../../context/WorkspaceContext";
import { Button } from "../ui/Button";
import { ChatInput } from "./ChatInput";
import { ChatMessage } from "./ChatMessage";

export function ChatWindow({ repositoryId, conversationId, setConversationId, disabled, className }) {
  const { selectCitation, activeCitation } = useWorkspace();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const controllerRef = useRef(null);
  const scrollRef = useRef(null);
  const [resolvedConversationId, setResolvedConversationId] = useState(
    conversationId ?? null
  );

  // Track external conversationId changes (e.g. switching conversations).
  useEffect(() => {
    setResolvedConversationId(conversationId ?? null);
  }, [conversationId]);

  useEffect(() => {
    if (!resolvedConversationId) {
      setMessages([]);
      setLoading(false);
      setError(null);
      return;
    }
    loadConversation(resolvedConversationId);
  }, [resolvedConversationId, repositoryId]);

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
  }

  function handleAnswer(result) {
    // A new conversation was created — propagate the id upward.
    if (result.conversation_id && setConversationId) {
      setConversationId(result.conversation_id);
      setResolvedConversationId(result.conversation_id);
    }

    const userMsg = {
      id: crypto.randomUUID(),
      role: "user",
      content: result.question,
      citations: [],
      created_at: new Date().toISOString(),
    };

    const assistantMsg = {
      id: result.message_id ?? crypto.randomUUID(),
      role: "assistant",
      content: result.answer,
      citations: result.citations ?? [],
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    if (result.citations && result.citations.length > 0) {
      selectCitation(result.citations[0]);
    }
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
      </div>
    );
  }

  return (
    <div
      className={"h-full flex flex-col min-h-[300px] " + (className ?? "")}
    >
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
            Start a conversation by asking a question.
          </div>
        )}
      </div>

      <ChatInput
        repositoryId={repositoryId}
        conversationId={resolvedConversationId}
        onAnswer={handleAnswer}
        disabled={disabled}
      />
    </div>
  );
}
