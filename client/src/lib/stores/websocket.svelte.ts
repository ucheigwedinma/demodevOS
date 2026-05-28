/**
 * Real-time WebSocket store for notifications and live data updates.
 *
 * Usage:
 *   import { ws } from "$lib/stores/websocket.svelte";
 *
 *   // Connect (call once after login, e.g. in root layout)
 *   ws.connect(token);
 *
 *   // Read reactive state
 *   ws.connected       // boolean
 *   ws.unreadCount      // number
 *   ws.lastNotification // latest notification object
 *   ws.lastDataChange   // latest data change event
 *
 *   // Mark a notification as read
 *   ws.markRead(notificationId);
 *
 *   // Listen for data changes (in a component)
 *   $effect(() => {
 *     const change = ws.lastDataChange;
 *     if (change?.model === "PurchaseOrder") refetchPOs();
 *   });
 */

interface WSNotification {
  id: number;
  title: string;
  message: string;
  severity: string;
  category: string;
  link_url: string;
  created_at: string;
}

interface WSDataChange {
  model: string;
  action: "created" | "updated" | "deleted";
  id: number | null;
  summary: string;
}

export interface PresenceUser {
  user_id: number;
  name: string;
  email: string;
  avatar_url: string;
  role: string;
  status: "online" | "offline";
  page: string;
}

export interface EditorInfo {
  user_id: number;
  name: string;
  email: string;
  avatar_url: string;
  role: string;
}

function createWebSocketStore() {
  let socket: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let reconnectAttempts = 0;
  const MAX_RECONNECT_DELAY = 30000;

  let connected = $state(false);
  let unreadCount = $state(0);
  let lastNotification = $state<WSNotification | null>(null);
  let lastDataChange = $state<WSDataChange | null>(null);
  let onlineUsers = $state<PresenceUser[]>([]);
  let activeEditors = $state<Map<string, EditorInfo>>(new Map());
  let currentToken = "";

  function getWsUrl(token: string): string {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    return `${protocol}//${host}/ws/notifications/?token=${token}`;
  }

  function connect(token: string) {
    if (socket && socket.readyState <= WebSocket.OPEN) {
      socket.close();
    }
    currentToken = token;
    reconnectAttempts = 0;
    _connect();
  }

  function _connect() {
    if (!currentToken) return;

    try {
      socket = new WebSocket(getWsUrl(currentToken));
    } catch {
      _scheduleReconnect();
      return;
    }

    socket.onopen = () => {
      connected = true;
      reconnectAttempts = 0;
    };

    socket.onclose = () => {
      connected = false;
      _scheduleReconnect();
    };

    socket.onerror = () => {
      connected = false;
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        switch (data.type) {
          case "notification.count":
            unreadCount = data.count;
            break;
          case "notification.new":
            lastNotification = data.notification;
            break;
          case "data.changed":
            lastDataChange = {
              model: data.model,
              action: data.action,
              id: data.id,
              summary: data.summary || "",
            };
            break;
          case "presence.roster":
            // Full list of online users (received on connect)
            onlineUsers = (data.users || []).map((u: any) => ({
              ...u,
              status: "online" as const,
            }));
            break;
          case "presence.update": {
            const user = data.user as PresenceUser;
            if (data.status === "offline") {
              onlineUsers = onlineUsers.filter(u => u.user_id !== user.user_id);
            } else {
              const existing = onlineUsers.find(u => u.user_id === user.user_id);
              if (existing) {
                onlineUsers = onlineUsers.map(u =>
                  u.user_id === user.user_id
                    ? { ...u, status: "online" as const, page: data.page || "" }
                    : u
                );
              } else {
                onlineUsers = [...onlineUsers, { ...user, status: "online", page: data.page || "" }];
              }
            }
            break;
          }
          case "editing.update": {
            const key = `${data.model}:${data.record_id}`;
            if (data.action === "started") {
              const next = new Map(activeEditors);
              next.set(key, data.user as EditorInfo);
              activeEditors = next;
            } else if (data.action === "stopped") {
              const next = new Map(activeEditors);
              next.delete(key);
              activeEditors = next;
            }
            break;
          }
          case "editing.status": {
            const key = `${data.model}:${data.record_id}`;
            if (data.editor) {
              const next = new Map(activeEditors);
              next.set(key, data.editor as EditorInfo);
              activeEditors = next;
            } else {
              const next = new Map(activeEditors);
              next.delete(key);
              activeEditors = next;
            }
            break;
          }
        }
      } catch {
        // Ignore malformed messages
      }
    };
  }

  function _scheduleReconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (!currentToken) return;

    // Don't spam reconnect — back off aggressively
    const delay = Math.min(5000 * 2 ** Math.min(reconnectAttempts, 5), MAX_RECONNECT_DELAY);
    reconnectAttempts++;
    // Only reconnect if we've successfully connected before or it's the first few attempts
    if (reconnectAttempts <= 3 || reconnectAttempts % 6 === 0) {
      reconnectTimer = setTimeout(_connect, delay);
    } else {
      // Still schedule but with longer delay to avoid flooding
      reconnectTimer = setTimeout(_connect, MAX_RECONNECT_DELAY);
    }
  }

  function disconnect() {
    currentToken = "";
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (socket) {
      socket.onclose = null; // Prevent reconnect
      socket.close();
      socket = null;
    }
    connected = false;
  }

  function markRead(notificationId: number) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "mark_read", id: notificationId }));
    }
  }

  function setPage(page: string) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "presence.page", page }));
    }
  }

  function startEditing(model: string, recordId: number | string) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "editing.start", model, record_id: recordId }));
    }
  }

  function stopEditing(model: string, recordId: number | string) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "editing.stop", model, record_id: recordId }));
    }
  }

  function checkEditing(model: string, recordId: number | string) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "editing.check", model, record_id: recordId }));
    }
  }

  function getEditor(model: string, recordId: number | string): EditorInfo | null {
    return activeEditors.get(`${model}:${recordId}`) || null;
  }

  return {
    get connected() { return connected; },
    get unreadCount() { return unreadCount; },
    get lastNotification() { return lastNotification; },
    get lastDataChange() { return lastDataChange; },
    get onlineUsers() { return onlineUsers; },
    get activeEditors() { return activeEditors; },
    connect,
    disconnect,
    markRead,
    setPage,
    startEditing,
    stopEditing,
    checkEditing,
    getEditor,
  };
}

export const ws = createWebSocketStore();
