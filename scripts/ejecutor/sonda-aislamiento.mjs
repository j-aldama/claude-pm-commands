// Sonda de aislamiento del ejecutor (D4). valida_impl.py la corre dentro del contenedor antes de los comandos del plan,
// en cada validación, y compara cada valor con lo esperado: si algo no cuadra, no se juzga (rc 2).
// Solo mide; nunca imprime el contenido del marcador ni de variables.
import fs from 'node:fs';
import net from 'node:net';
import dns from 'node:dns/promises';
import { spawn } from 'node:child_process';

const r = {};
const intenta = async (nombre, fn) => {
  try { r[nombre] = `ok ${(await fn()) ?? ''}`.trim(); } catch (e) { r[nombre] = `error ${e.code || e.message}`; }
};

r.canario = process.env.VALIDA_CANARIO ? 'presente' : 'ausente';
r.openai_api_key = process.env.OPENAI_API_KEY ? 'presente' : 'ausente';
await intenta('escribir_raiz', () => fs.writeFileSync('/usr/local/marca-sonda', 'x'));
await intenta('escribir_origen', () => fs.writeFileSync(`${process.env.VALIDA_ORIGEN || '/origen'}/.marca-sonda`, 'x'));
await intenta('escribir_tmp', () => { fs.writeFileSync('/tmp/marca-sonda', 'x'); fs.unlinkSync('/tmp/marca-sonda'); });
await intenta('leer_home_anfitrion', () => fs.readdirSync('/Users').length);
await intenta('marcador_anfitrion', () => fs.readFileSync(process.env.VALIDA_MARCADOR || '/no-definido', 'utf8').length);
await intenta('loopback', () => new Promise((ok, mal) => {
  const s = net.createServer((c) => c.end('hola')).listen(0, '127.0.0.1', () => {
    const c = net.connect(s.address().port, '127.0.0.1');
    c.on('data', () => { c.destroy(); s.close(); ok(); });
    c.on('error', mal);
  });
  s.on('error', mal);
}));
await intenta('internet', () => new Promise((ok, mal) => {
  const c = net.connect(443, '1.1.1.1', () => { c.destroy(); ok('CONECTO'); });
  c.setTimeout(3000, () => { c.destroy(); mal(new Error('ETIMEDOUT')); });
  c.on('error', mal);
}));
await intenta('dns_lookup', async () => (await dns.lookup('example.com')).address);
await intenta('dns_resolve4', async () => (await dns.resolve4('example.com')).join(','));
await intenta('cgroup', () => ['pids.max', 'memory.max', 'cpu.max']
  .map((f) => `${f}=${fs.readFileSync(`/sys/fs/cgroup/${f}`, 'utf8').trim()}`).join(' '));
await intenta('disco', () => fs.writeFileSync('/tmp/relleno-sonda', Buffer.alloc(40 * 1024 * 1024)));
try { fs.unlinkSync('/tmp/relleno-sonda'); } catch { /* no se escribió */ }
await intenta('procesos', () => new Promise((ok, mal) => {
  const hijos = [];
  let fallo = null;
  for (let i = 0; i < 200 && !fallo; i += 1) {
    try {
      const h = spawn('sleep', ['3']);
      h.on('error', (e) => { fallo = fallo || e; });
      hijos.push(h);
    } catch (e) { fallo = e; }
  }
  setTimeout(() => {
    hijos.forEach((h) => { try { h.kill(); } catch { /* ya terminó */ } });
    const vivos = hijos.filter((h) => h.pid).length;
    if (fallo) mal(Object.assign(new Error(`${fallo.code} tras ${vivos} hijos`), { code: `${fallo.code} tras ${vivos} hijos` }));
    else ok(`${vivos} hijos sin tope`);
  }, 500);
}));
console.log(JSON.stringify(r));
