import index from './index.html';

const server = Bun.serve({
  port: 3000,
  async fetch(req) {
    const url = new URL(req.url);

    if (url.pathname === "/") {
      return new Response(Bun.file("./index.html"));
    }

    if (url.pathname === "/style.css") {
      return new Response(Bun.file("./style.css"));
    }

    if (url.pathname === "/script.js") {
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

    return new Response("Not Found", { status: 404 });
  }
});
console.log(`Listening on ${server.url}`);