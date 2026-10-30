// Optional dependency-free static development server. The app itself runs in the browser.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const files = new Set(['index.html','style.css','app.js','bank.js','favicon.svg']);
const types = {'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.svg':'image/svg+xml'};
const port = Number(process.env.PORT || 8000);
http.createServer((req, res) => {
  const file = new URL(req.url, 'http://localhost').pathname.slice(1) || 'index.html';
  if (!files.has(file)) { res.writeHead(404); res.end('Not found'); return; }
  fs.readFile(path.join(__dirname, file), (error, bytes) => {
    if (error) { res.writeHead(500); res.end('Could not read file'); return; }
    res.writeHead(200, {'Content-Type':types[path.extname(file)], 'X-Content-Type-Options':'nosniff', 'Cache-Control':'no-cache', 'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'"});
    res.end(bytes);
  });
}).listen(port, '127.0.0.1', () => console.log(`Salt Bank: http://127.0.0.1:${port}`));
