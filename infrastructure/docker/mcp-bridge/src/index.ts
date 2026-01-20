
import express from 'express';
import { WebSocketServer, WebSocket } from 'ws';
import { spawn } from 'cross-spawn';
import { ChildProcessWithoutNullStreams } from 'child_process';
import fs from 'fs';
import path from 'path';
import http from 'http';

// Types for Server Config
interface ServerConfig {
    command: string;
    args: string[];
    env?: Record<string, string>;
}

interface ServerMap {
    [key: string]: ServerConfig;
}

// Load Configuration
const CONFIG_PATH = path.join(__dirname, '../servers.json');
let servers: ServerMap = {};

try {
    if (fs.existsSync(CONFIG_PATH)) {
        servers = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
    } else {
        console.warn(`Warning: Config file not found at ${CONFIG_PATH}`);
    }
} catch (error) {
    console.error("Failed to load servers.json:", error);
}

const app = express();
const server = http.createServer(app);
const wss = new WebSocketServer({ noServer: true });

const PORT = 8000;

app.get('/health', (req, res) => {
    res.json({ status: 'ok', servers: Object.keys(servers) });
});

app.get('/servers', (req, res) => {
    res.json(servers);
});

// Handle WebSocket Upgrades
server.on('upgrade', (request, socket, head) => {
    const url = new URL(request.url || '', `http://${request.headers.host}`);
    const pathname = url.pathname;  // e.g. /mcp/fetch

    // Expected format: /mcp/:serverName
    const match = pathname.match(/^\/mcp\/([a-zA-Z0-9_-]+)$/);

    if (!match) {
        socket.write('HTTP/1.1 404 Not Found\r\n\r\n');
        socket.destroy();
        return;
    }

    const serverName = match[1];
    const config = servers[serverName];

    if (!config) {
        console.log(`Connection rejected: Unknown server '${serverName}'`);
        socket.write('HTTP/1.1 404 Not Found\r\n\r\n');
        socket.destroy();
        return;
    }

    wss.handleUpgrade(request, socket, head, (ws) => {
        wss.emit('connection', ws, request, config, serverName);
    });
});

wss.on('connection', (ws: WebSocket, request: any, config: ServerConfig, serverName: string) => {
    console.log(`[${serverName}] Client connected`);

    let childEnv = { ...process.env, ...config.env };
    // For npx/node-based tools, we might need to ensure PATH is correct or critical vars are passed

    console.log(`[${serverName}] Spawning: ${config.command} ${config.args.join(' ')}`);

    let child: ChildProcessWithoutNullStreams | null = null;

    try {
        child = spawn(config.command, config.args, {
            env: childEnv,
            cwd: process.cwd(), // or a specific workspace dir
            shell: false // Use shell: false for better signal handling, unless command needs caching
        });
    } catch (e: any) {
        console.error(`[${serverName}] Spawn error:`, e);
        ws.close(1011, `Failed to spawn process: ${e.message}`);
        return;
    }

    if (!child || !child.stdout || !child.stdin) {
        console.error(`[${serverName}] Child process failed to start properly`);
        ws.close(1011, "Process start failure");
        return;
    }

    // --- PIPING LOGIC ---

    // 1. STDOUT -> WebSocket
    // JSON-RPC messages are usually newline delimited. 
    // We buffer data and emit complete lines.
    let buffer = '';
    child.stdout.on('data', (data: Buffer) => {
        const chunk = data.toString();
        buffer += chunk;

        const lines = buffer.split('\n');
        // The last item is either empty string (if ends with newline) or the incomplete chunk
        buffer = lines.pop() || '';

        for (const line of lines) {
            if (line.trim()) {
                // Check if the connection is still open before sending
                if (ws.readyState === WebSocket.OPEN) {
                    // console.log(`[${serverName}] STDOUT >> ${line.substring(0, 100)}...`); 
                    ws.send(line);
                }
            }
        }
    });

    // 2. WebSocket -> STDIN
    ws.on('message', (message: string) => {
        // console.log(`[${serverName}] WS << ${message.toString().substring(0, 50)}...`);
        if (child && child.stdin) {
            child.stdin.write(message.toString() + "\n");
        }
    });

    // 3. STDERR -> Console (Logging)
    child.stderr.on('data', (data: Buffer) => {
        console.error(`[${serverName}] STDERR: ${data.toString().trim()}`);
    });

    // 4. Cleanup
    const cleanup = () => {
        console.log(`[${serverName}] Cleaning up connection`);
        if (child) {
            child.kill();
            child = null;
        }
    };

    ws.on('close', cleanup);
    ws.on('error', (err) => {
        console.error(`[${serverName}] WebSocket error:`, err);
        cleanup();
    });

    child.on('close', (code: number | null) => {
        console.log(`[${serverName}] Process exited with code ${code}`);
        if (ws.readyState === WebSocket.OPEN) {
            ws.close(1000, "Process exited");
        }
    });
});

server.listen(PORT, () => {
    console.log(`MCP Bridge Server listening on port ${PORT}`);
    console.log('Available servers:');
    Object.keys(servers).forEach(name => {
        console.log(`- ws://localhost:${PORT}/mcp/${name} -> ${servers[name].command} ${servers[name].args.join(' ')}`);
    });
});
