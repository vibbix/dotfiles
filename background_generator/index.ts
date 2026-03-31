import index from './index.html';
import { watch } from 'fs';

const server = Bun.serve({
  port: 3000,
  async fetch(req, server) {
    const url = new URL(req.url);

    if (url.pathname === "/") {
      return new Response(Bun.file("./index.html"));
    }

    // Upgrade the connection to a WebSocket for hot-reloading
    if (url.pathname === "/hot-reload") {
      const upgraded = server.upgrade(req);
      if (!upgraded) {
        return new Response("Upgrade failed", { status: 400 });
      }
      return;
    }

    if (url.pathname === "/style.css") {
      return new Response(Bun.file("./style.css"));
    }

    if (url.pathname === "/script.ts") {
      // Use Bun's bundler to automatically compile the script and resolve `three` 
      // module imports from node_modules into a single JS file
      const build = await Bun.build({
        entrypoints: ['./script.ts'],
      });

      if (!build.success) {
        console.error("Build failed:", build.logs);
        return new Response("Build failed", { status: 500 });
      }

      return new Response(build.outputs[0], {
        headers: {
          "Content-Type": "application/javascript",
        },
      });
    }

    if (url.pathname.startsWith("/logos/") || url.pathname.startsWith("/models/")) {
      return new Response(Bun.file("." + url.pathname));
    }

    return new Response("Not Found", { status: 404 });
  },
  websocket: {
    open(ws) {
      ws.subscribe("hot-reload");
    },
    message(ws, message) {},
  }
});

// Watch current directory and notify WebSocket clients to reload upon changes
watch(import.meta.dir, { recursive: true }, (event, filename) => {
  console.log(`Detected ${event} in ${filename}. Reloading...`);
  server.publish("hot-reload", "reload");
});

console.log(`Listening on ${server.url}`);