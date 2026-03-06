import { useCallback, useEffect, useRef, useState } from "react";

export type WSStatus = "connecting" | "open" | "closing" | "closed" | "error";
export type IncomingMessage = Record<string, any>;
export type OutgoingMessage = Record<string, any>;

export interface UseChatWebSocketOptions {
  url?: string; // e.g. ws://localhost:8000/ws/42
  onMessage?: (msg: IncomingMessage) => void;
  onOpen?: () => void;
  onClose?: (ev?: CloseEvent) => void;
  onError?: (ev?: Event) => void;
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  heartbeatIntervalMs?: number;
  reconnectBaseMs?: number;
}

export function useChatWebSocket(options: UseChatWebSocketOptions) {
  const {
    url,
    onMessage,
    onOpen,
    onClose,
    onError,
    autoReconnect = true,
    maxReconnectAttempts = 10,
    heartbeatIntervalMs = 20000,
    reconnectBaseMs = 1000,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const heartbeatTimerRef = useRef<number | null>(null);
  const sendQueueRef = useRef<OutgoingMessage[]>([]);
  const manuallyClosedRef = useRef(false);

  const [status, setStatus] = useState<WSStatus>("closed");

  // message history and metadata
  const [messages, setMessages] = useState<IncomingMessage[]>([]);
  const [historyMeta, setHistoryMeta] = useState<{
    total?: number;
    page?: number;
    per_page?: number;
    next_page?: number | null;
    prev_page?: number | null;
  } | null>(null);

  const clearHeartbeat = () => {
    if (heartbeatTimerRef.current) {
      window.clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  };

  const startHeartbeat = (ws: WebSocket) => {
    clearHeartbeat();
    heartbeatTimerRef.current = window.setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify({ type: "ping", ts: Date.now() }));
        } catch (e) {
          // ignore
        }
      }
    }, heartbeatIntervalMs) as unknown as number;
  };

  const flushQueue = (ws: WebSocket) => {
    while (sendQueueRef.current.length && ws.readyState === WebSocket.OPEN) {
      const msg = sendQueueRef.current.shift();
      if (msg) {
        try {
          ws.send(JSON.stringify(msg));
        } catch (e) {
          console.error("Failed to send queued message", e);
        }
      }
    }
  };

  const handleIncoming = useCallback(
    (data: IncomingMessage) => {
      // give consumer first crack at raw messages
      onMessage?.(data);

      // handle typed events from server
      const type = data?.type;
      if (type === "history_update") {
        // server may send either a paginated dict or a plain list under `messages` or `items`
        const payload = data.messages ?? data.items ?? [];
        if (Array.isArray(payload)) {
          setMessages(payload);
        }
        // if the server sends metadata, capture it
        if (data.total || data.page) {
          setHistoryMeta({
            total: data.total,
            page: data.page,
            per_page: data.per_page,
            next_page: data.next_page,
            prev_page: data.prev_page,
          });
        } else if (data.items && (data.total || data.page)) {
          setHistoryMeta({
            total: data.total,
            page: data.page,
            per_page: data.per_page,
            next_page: data.next_page,
            prev_page: data.prev_page,
          });
        }
      } else if (type === "new_message" || type === "message_sent") {
        // append new incoming message to history
        const item = data as IncomingMessage;
        setMessages((prev: IncomingMessage[]) => [...prev, item]);
      } else if (type === "message_seen") {
        // mark message(s) as seen in local history when server notifies
        const chatId = data.chat_id;
        setMessages((prev: IncomingMessage[]) =>
          prev.map((m) => (m.id === chatId ? { ...m, is_seen: true } : m)),
        );
      } else if (type === "unread_count") {
        // could be used by consumer to update badge UI; keep it in meta
        setHistoryMeta(
          (
            prev: {
              total?: number;
              page?: number;
              per_page?: number;
              next_page?: number | null;
              prev_page?: number | null;
            } | null,
          ) => ({
            ...(prev ?? {}),
            total: data.count ?? prev?.total,
          }),
        );
      }
    },
    [onMessage],
  );

  const connect = useCallback(() => {
    manuallyClosedRef.current = false;
    setStatus("connecting");
    const ws = new WebSocket(url!);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectAttemptsRef.current = 0;
      setStatus("open");
      startHeartbeat(ws);
      flushQueue(ws);
      onOpen?.();
    };

    ws.onmessage = (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data);
        handleIncoming(data);
      } catch (e) {
        onMessage?.({ raw: ev.data });
      }
    };

    ws.onclose = (ev: CloseEvent) => {
      clearHeartbeat();
      wsRef.current = null;
      setStatus("closed");
      onClose?.(ev);

      if (!manuallyClosedRef.current && autoReconnect) {
        const attempt = reconnectAttemptsRef.current + 1;
        reconnectAttemptsRef.current = attempt;
        if (attempt <= maxReconnectAttempts) {
          const delay = Math.min(30000, reconnectBaseMs * 2 ** (attempt - 1));
          setStatus("connecting");
          setTimeout(() => {
            connect();
          }, delay);
        } else {
          setStatus("closed");
        }
      }
    };

    ws.onerror = (ev: Event) => {
      setStatus("error");
      onError?.(ev);
    };
  }, [
    url,
    onMessage,
    onOpen,
    onClose,
    onError,
    autoReconnect,
    maxReconnectAttempts,
    reconnectBaseMs,
    heartbeatIntervalMs,
    handleIncoming,
  ]);

  useEffect(() => {
    if (!url) {
      setStatus("closed");
      return;
    }
    connect();
    return () => {
      manuallyClosedRef.current = true;
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        setStatus("closing");
        wsRef.current.close();
      }
      clearHeartbeat();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  const sendJson = useCallback((msg: OutgoingMessage) => {
    const ws = wsRef.current;
    try {
      console.debug("WS ->", msg, "state:", ws?.readyState);
    } catch (e) {
      // ignore logging failures
    }
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    } else {
      sendQueueRef.current.push(msg);
    }
  }, []);

  // helper API matching server actions
  const joinChat = useCallback(
    (chatWith: number, opts?: { page?: number; per_page?: number }) => {
      // include both common keys to maximize server compatibility
      const payload: any = {
        action: "join_chat",
        chat_with: chatWith,
        to: chatWith,
      };
      if (opts?.page) payload.page = opts.page;
      if (opts?.per_page) payload.per_page = opts.per_page;
      sendJson(payload);
    },
    [sendJson],
  );

  const leaveChat = useCallback(() => {
    sendJson({ action: "leave_chat" });
  }, [sendJson]);

  const sendMessage = useCallback(
    (to: number, text: string) => {
      sendJson({ action: "send_message", to, text });
    },
    [sendJson],
  );

  const markSeen = useCallback(
    (chat_id: number) => {
      sendJson({
        action: "mark_seen",
        chat_id,
        to: chat_id,
        chat_with: chat_id,
      });
    },
    [sendJson],
  );

  const loadMore = useCallback(
    async (chatWith: number, page = 2, per_page = 20) => {
      // try REST endpoint fallback to fetch older pages (useful if WS doesn't support load_more)
      try {
        const { origin } = window.location;
        const res = await fetch(
          `${origin}/api/v1/chats/with/${chatWith}?page=${page}&per_page=${per_page}`,
          {
            credentials: "include",
            headers: { Accept: "application/json" },
          },
        );
        if (!res.ok) throw new Error(`status=${res.status}`);
        const body = await res.json();
        const items = body.items ?? body;
        if (Array.isArray(items)) {
          // prepend older items if loading earlier pages
          setMessages((prev) => [...items, ...prev]);
        }
        if (body.total || body.page) {
          setHistoryMeta({
            total: body.total,
            page: body.page,
            per_page: body.per_page,
            next_page: body.next_page,
            prev_page: body.prev_page,
          });
        }
        return body;
      } catch (e) {
        console.error("loadMore failed", e);
        return null;
      }
    },
    [],
  );

  const close = useCallback(() => {
    manuallyClosedRef.current = true;
    if (wsRef.current) {
      try {
        setStatus("closing");
        wsRef.current.close();
      } catch (e) {
        // ignore
      }
    }
    clearHeartbeat();
  }, []);

  const clearMessages = useCallback(() => setMessages([]), []);

  return {
    sendJson,
    joinChat,
    leaveChat,
    sendMessage,
    markSeen,
    loadMore,
    clearMessages,
    close,
    status,
    messages,
    historyMeta,
    reconnectAttempts: reconnectAttemptsRef.current,
    rawWebSocket: wsRef.current,
  };
}
