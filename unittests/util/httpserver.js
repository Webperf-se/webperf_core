import handler from 'serve-handler';
import { createServer } from 'node:http';

let server;
const port = 3000;
const host = '127.0.0.1';

export async function startServer() {
  server = createServer((request, response) => {
    return handler(request, response, { public: './unittests/data/' });
  });

  return server.listen(port, host, () => {});
}
export async function stopServer() {
  return server.close();
}