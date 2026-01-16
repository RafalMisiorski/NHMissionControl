/**
 * InteractiveTerminal Component (EPOCH 9)
 *
 * Provides a full xterm.js terminal for interactive CC sessions.
 * Features:
 * - ANSI color support
 * - Proper cursor handling
 * - Auto-resize
 * - Web links detection
 * - Prompt input
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';
import { Send, RotateCcw, Square, Loader2 } from 'lucide-react';

interface InteractiveTerminalProps {
  sessionId: string;
  status: string;
  onSendPrompt: (prompt: string) => void;
  onSendInput: (text: string) => void;
  onStop: () => void;
  onKill: () => void;
  initialOutput?: string[];
}

export function InteractiveTerminal({
  sessionId,
  status,
  onSendPrompt,
  onSendInput,
  onStop,
  onKill,
  initialOutput = [],
}: InteractiveTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminalInstance = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const [prompt, setPrompt] = useState('');
  const [isConnected, setIsConnected] = useState(false);

  // Initialize terminal
  useEffect(() => {
    if (!terminalRef.current || terminalInstance.current) return;

    // Create terminal with dark theme
    const terminal = new Terminal({
      theme: {
        background: '#1a1b26',
        foreground: '#a9b1d6',
        cursor: '#c0caf5',
        cursorAccent: '#1a1b26',
        selectionBackground: '#33467C',
        black: '#32344a',
        red: '#f7768e',
        green: '#9ece6a',
        yellow: '#e0af68',
        blue: '#7aa2f7',
        magenta: '#ad8ee6',
        cyan: '#449dab',
        white: '#787c99',
        brightBlack: '#444b6a',
        brightRed: '#ff7a93',
        brightGreen: '#b9f27c',
        brightYellow: '#ff9e64',
        brightBlue: '#7da6ff',
        brightMagenta: '#bb9af7',
        brightCyan: '#0db9d7',
        brightWhite: '#acb0d0',
      },
      fontFamily: '"Cascadia Code", "Fira Code", monospace',
      fontSize: 14,
      lineHeight: 1.2,
      cursorBlink: true,
      cursorStyle: 'bar',
      scrollback: 10000,
      convertEol: true,
    });

    // Add fit addon
    const fit = new FitAddon();
    terminal.loadAddon(fit);
    fitAddon.current = fit;

    // Add web links addon
    const webLinks = new WebLinksAddon();
    terminal.loadAddon(webLinks);

    // Open terminal in container
    terminal.open(terminalRef.current);
    fit.fit();

    // Store reference
    terminalInstance.current = terminal;

    // Write initial output
    if (initialOutput.length > 0) {
      terminal.writeln('\x1b[90m--- Previous Output ---\x1b[0m');
      initialOutput.forEach((line) => {
        terminal.writeln(line);
      });
      terminal.writeln('\x1b[90m--- End Previous Output ---\x1b[0m\n');
    }

    // Handle resize
    const handleResize = () => {
      if (fitAddon.current) {
        fitAddon.current.fit();
      }
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      terminal.dispose();
      terminalInstance.current = null;
    };
  }, [initialOutput]);

  // Connect WebSocket
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/cc-sessions/${sessionId}/stream`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      if (terminalInstance.current) {
        terminalInstance.current.writeln('\x1b[32m✓ Connected to session\x1b[0m\n');
      }
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (terminalInstance.current) {
        switch (message.type) {
          case 'output':
            terminalInstance.current.writeln(message.data.content);
            break;

          case 'status_change':
            terminalInstance.current.writeln(
              `\x1b[33m[Status: ${message.data.old_status} → ${message.data.new_status}]\x1b[0m`
            );
            break;

          case 'tool_call':
            terminalInstance.current.writeln(
              `\x1b[36m[Tool: ${message.data.tool_name}]\x1b[0m`
            );
            break;

          case 'thinking':
            terminalInstance.current.writeln(
              `\x1b[90m[Thinking: ${message.data.content?.substring(0, 100)}...]\x1b[0m`
            );
            break;

          case 'awaiting_input':
            terminalInstance.current.writeln(
              '\x1b[33m[Awaiting input...]\x1b[0m'
            );
            break;

          case 'error':
            terminalInstance.current.writeln(
              `\x1b[31m[Error: ${message.data.message}]\x1b[0m`
            );
            break;

          case 'close':
            terminalInstance.current.writeln(
              `\x1b[90m[Session closed: ${message.data.reason}]\x1b[0m`
            );
            break;

          case 'heartbeat':
            // Silent heartbeat
            break;

          default:
            // Unknown message type
            break;
        }
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      if (terminalInstance.current) {
        terminalInstance.current.writeln('\x1b[31m✗ Disconnected from session\x1b[0m');
      }
    };

    ws.onerror = () => {
      if (terminalInstance.current) {
        terminalInstance.current.writeln('\x1b[31m✗ WebSocket error\x1b[0m');
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId]);

  // Handle prompt submission
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!prompt.trim()) return;

      onSendPrompt(prompt);

      if (terminalInstance.current) {
        terminalInstance.current.writeln(`\x1b[34m> ${prompt}\x1b[0m`);
      }

      setPrompt('');
    },
    [prompt, onSendPrompt]
  );

  // Status indicator color
  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return 'text-green-400';
      case 'awaiting_input':
        return 'text-yellow-400';
      case 'completed':
        return 'text-blue-400';
      case 'failed':
      case 'crashed':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#1a1b26] rounded-lg overflow-hidden border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#24283b] border-b border-gray-700">
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">Session:</span>
          <code className="text-sm text-blue-400">{sessionId.slice(0, 8)}</code>
          <span className={`text-sm ${getStatusColor()}`}>
            {status === 'running' && <Loader2 className="inline w-4 h-4 mr-1 animate-spin" />}
            {status}
          </span>
          {isConnected && (
            <span className="text-xs text-green-500">● Connected</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onStop}
            className="px-3 py-1 text-sm bg-yellow-600 hover:bg-yellow-700 text-white rounded"
            title="Graceful stop"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={onKill}
            className="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 text-white rounded"
            title="Force kill"
          >
            <Square className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Terminal */}
      <div className="flex-1 p-2 overflow-hidden">
        <div ref={terminalRef} className="h-full" />
      </div>

      {/* Prompt input */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 px-4 py-3 bg-[#24283b] border-t border-gray-700"
      >
        <span className="text-green-400">❯</span>
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={
            status === 'awaiting_input'
              ? 'Enter your prompt...'
              : 'Session is running...'
          }
          disabled={status !== 'awaiting_input' && status !== 'idle'}
          className="flex-1 bg-transparent border-none outline-none text-gray-200 placeholder-gray-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={status !== 'awaiting_input' && status !== 'idle'}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded flex items-center gap-2"
        >
          <Send className="w-4 h-4" />
          Send
        </button>
      </form>
    </div>
  );
}

export default InteractiveTerminal;
