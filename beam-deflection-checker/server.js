const http = require('node:http');
const fs = require('node:fs/promises');
const path = require('node:path');

const assets = {
  '/': ['index.html', 'text/html'],
  '/index.html': ['index.html', 'text/html'],
  '/styles.css': ['styles.css', 'text/css'],
  '/comparison.css': ['comparison.css', 'text/css'],
  '/beam.js': ['beam.js', 'text/javascript'],
  '/app.js': ['app.js', 'text/javascript'],
  '/sections.js': ['sections.js', 'text/javascript'],
  '/section-ui.js': ['section-ui.js', 'text/javascript'],
  '/awatif-analysis.mjs': ['awatif-analysis.mjs', 'text/javascript'],
  '/dist/awatif/deformCpp.js': ['dist/awatif/deformCpp.js', 'text/javascript'],
  '/dist/awatif/cpp/built/deform.js': ['dist/awatif/cpp/built/deform.js', 'text/javascript'],
  '/dist/awatif/cpp/built/deform.wasm': ['dist/awatif/cpp/built/deform.wasm', 'application/wasm'],
};
const port = Number(process.env.PORT || 3000);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  console.error('PORT must be an integer between 1 and 65535.');
  process.exit(1);
}
const server = http.createServer(async (req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405, { Allow: 'GET, HEAD' });
    return res.end('Method not allowed');
  }
  const pathname = (req.url || '/').split('?')[0];
  const asset = Object.hasOwn(assets, pathname) ? assets[pathname] : null;
  if (!asset) {
    res.writeHead(404);
    return res.end('Not found');
  }
  try {
    const data = await fs.readFile(path.join(__dirname, asset[0]));
    res.writeHead(200, { 'Content-Type': asset[1] === 'application/wasm' ? asset[1] : `${asset[1]}; charset=utf-8`, 'Cache-Control': 'no-store' });
    res.end(req.method === 'HEAD' ? undefined : data);
  } catch (error) {
    console.error(error.message);
    res.writeHead(500);
    res.end('Unable to read application file');
  }
});
server.on('error', error => {
  console.error(error.code === 'EADDRINUSE'
    ? `Port ${port} is already in use. Stop the other server or set PORT to another port.`
    : error.message);
  process.exit(1);
});
server.listen(port, '127.0.0.1', () => {
  console.log(`Beam deflection checker: http://127.0.0.1:${port}`);
  console.log('Press Ctrl+C to stop.');
});
