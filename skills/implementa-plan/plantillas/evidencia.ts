// Fixture de evidencia por paso para @playwright/test (plantilla de /implementa-plan).
//
// `paso` (con navegador): cada paso deja captura de pantalla completa, consola y errores de la página, peticiones
// fallidas o con estado >= 400 y URL. `pasoApi` (sin navegador, para casos de API con el fixture `request`): la captura
// del paso es de texto, lo que el cuerpo anota con `anota(...)` (la petición y la respuesta) en paso-NN.txt. Los dos
// llevan duración y resultado. Escribe <EVIDENCIA_DIR>/<caso>/pasos.json después de CADA paso (de
// forma atómica), con el commit (HEAD) que se probó y la ruta del spec relativa a la raíz del repo. El HTML lo arma
// `implementa_plan.py evidencia`.
//
// Todo texto capturado pasa por `depura` (los mismos patrones que SECRETOS en implementa_plan.py y DEPURACION en
// evidencia_pw.py: si cambias uno, cambia los tres). Las capturas tapan siempre los campos de contraseña, códigos
// de un solo uso, tarjetas y lo marcado con data-sensible; además, cualquier texto con forma de secreto
// (TOKEN_VISIBLE) y los input/textarea cuyo valor la tenga o cuyo nombre, id, placeholder, aria-label o autocomplete
// digan que guardan uno (NOMBRE_SENSIBLE).
//
// Uso (el ID del caso va en el título, como en los casos manuales: M-01, M-02...):
//
//   import { test, expect } from './evidencia';
//   test('M-03 rechaza un correo ya registrado', async ({ page, paso }) => {
//     await paso('Abrir el registro', 'Se ve el formulario vacío', async () => {
//       await page.goto('/registro');
//       await expect(page.getByRole('heading', { name: 'Crear cuenta' })).toBeVisible();
//     });
//     await paso('Enviar un correo ya registrado', 'Aparece «Ese correo ya existe» y no se crea la cuenta',
//       async () => { ... },
//       { mascara: [page.getByLabel('Teléfono')] });
//   });
//
//   test('M-07 la API rechaza cantidad cero', async ({ request, pasoApi }) => {
//     await pasoApi('POST /api/pedidos con cantidad 0', 'Responde 400 con «cantidad inválida»', async (anota) => {
//       const r = await request.post('/api/pedidos', { data: { cantidad: 0 } });
//       anota(`POST /api/pedidos {"cantidad":0}\n${r.status()} ${await r.text()}`);
//       expect(r.status()).toBe(400);
//     });
//   });
//
// Un paso de `pasoApi` que pasa tiene que anotar algo: sin captura ni texto, `implementa_plan.py evidencia` lo rechaza.
// Si falla, su error queda en la captura de texto aunque no haya anotado nada.
//
// Corrida de evidencia: EVIDENCIA_DIR=<dir> EVIDENCIA_CORRIDA=<id único> npx playwright test --retries=0
// --project=<uno>. Con EVIDENCIA_CORRIDA, un reintento o el mismo caso en otro proyecto truenan en vez de pisar la
// evidencia. Sin EVIDENCIA_DIR escribe en test-results/evidencia (que debe estar ignorado por git).
import { test as base, expect, type Locator, type Page, type TestInfo } from '@playwright/test';
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

type Registro = Record<string, string>;
type OpcionesPaso = { mascara?: Locator[] };
type Anota = (texto: unknown) => void;
type Paso = (accion: string, esperado: string, cuerpo: (anota: Anota) => Promise<void>, opciones?: OpcionesPaso)
  => Promise<void>;

const PARAMETRO_SENSIBLE = /(token|secret|passw|pwd|api[_-]?key|apikey|session|sig|auth|credential|code)/i;
const SELECTOR_SENSIBLE = 'input[type="password"], [autocomplete*="password"], [autocomplete="one-time-code"], '
  + '[autocomplete="cc-number"], [autocomplete="cc-csc"], [data-sensible]';
const MAX_TEXTO = 2000;
const MAX_CAPTURA_TEXTO = 20000;
// Corre en la página: marca los input/textarea (no ocultos) cuyo valor parece secreto o cuyo nombre dice que lo es.
const MARCA_CAMPOS_SENSIBLES = ([token, nombre]: [string, string]) => {
  const conToken = new RegExp(token, 'i');
  const sensible = new RegExp(nombre, 'i');
  document.querySelectorAll('input, textarea').forEach((el) => {
    const campo = el as HTMLInputElement;
    if (campo.type === 'hidden') return;
    const nombres = ['name', 'id', 'placeholder', 'aria-label', 'autocomplete'].map((a) => campo.getAttribute(a) ?? '')
      .join(' ').replace(/([a-z0-9])([A-Z])/g, '$1_$2');
    if (conToken.test(campo.value) || sensible.test(nombres)) campo.setAttribute('data-evidencia-token', '');
  });
};
const ID_CASO = /^M-\d{2,}$/;
const CLAVE = '[A-Za-z0-9_.-]{0,40}(?:pass(?:word|wd)?|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key'
  + '|credential|authorization|session(?:[_-]?id)?|cookie|contrase[ñn]a|secreto)(?:[_.-]?(?:key|id|hash|digest))?s?';
const ENCABEZADO = '(?:proxy-)?authorization|set-cookie|cookie|x-[a-z0-9-]{0,40}(?:auth|api-?key|token|secret)[a-z0-9-]{0,40}';
// Claves y cabeceras solo empiezan tras un delimitador (o al inicio): con \b, «x-auth-» × 30 000 tarda ~1 s en vez de 0.02 s.
const INICIO = `(?<![^\\s"'{,;(?&/])`;
const PROVEEDOR = 'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}'
  + '|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}|glpat-[A-Za-z0-9_-]{20,}|[rsp]k_(?:live|test)_[A-Za-z0-9]{16,}'
  + '|AKIA[0-9A-Z]{16}';
// Valor con forma de secreto en la pantalla: ≥ 8 caracteres con algún dígito, o ≥ 16 sin dígitos. «Basic information»
// y «Token generado» no entran; «Bearer abcdefghijklmnop» y «password: hunter2abc» sí.
const VALOR = '(?:(?=[A-Za-z0-9._~+/=-]*\\d)[A-Za-z0-9._~+/=-]{8,}|[A-Za-z0-9._~+/=-]{16,})';
// Secretos que se reconocen solos en el texto de la página: se tapan en la captura (mismo patrón en evidencia_pw.py).
const TOKEN_VISIBLE = new RegExp('-----BEGIN [A-Z ]{0,40}PRIVATE KEY-----'
  + '|\\beyJ[A-Za-z0-9_-]{8,}\\.[A-Za-z0-9_-]{8,}\\.[A-Za-z0-9_-]{8,}'
  + `|\\b(?:${PROVEEDOR})`
  + `|\\b(?:Basic|Digest|Bearer|Token|NTLM|Negotiate)\\s+${VALOR}`
  + `|${INICIO}(?:${CLAVE}|${ENCABEZADO})["']?\\s*[:=]\\s*["']?${VALOR}`
  + '|\\b[a-z][a-z0-9+.-]{0,30}://[^/\\s:@]{1,200}:[^/\\s@]{1,200}@', 'i');
// Nombre, id, placeholder, aria-label o autocomplete de un campo que guarda un secreto (mismo patrón en evidencia_pw.py),
// por componente del nombre (camelCase ya separado): «secretary_name» o «tokenization» no cuentan; «sessionId» sí.
const NOMBRE_SENSIBLE = new RegExp('(?:^|[^a-z])(?:pass(?:word|wd)?|pwd|secret|token|api[_ -]?key|private[_ -]?key'
  + '|access[_ -]?key|otp|one[_ -]?time|verification[_ -]?code|sms[_ -]?code|cvv|cvc|cc-number|cc-csc|card[_ -]?number'
  + '|auth|authorization|session(?:[_ -]?id)?|cookie|contrase[ñn]a|secreto|clave[_ -]?(?:de[_ -]?)?acceso|nip|pin'
  + '|c[oó]digo[_ -]?(?:de[_ -]?)?(?:verificaci[oó]n|seguridad|acceso))s?(?:$|[^a-z])', 'i');
const DEPURACION: [RegExp, string][] = [
  [/\u001b\[[0-9;]*m/g, ''],
  [/-----BEGIN ([A-Z ]{0,40})PRIVATE KEY-----[\s\S]*?(?:-----END \1PRIVATE KEY-----|$)/g, '*** llave privada ***'],
  [new RegExp(`${INICIO}(${ENCABEZADO})["']?\\s*[:=]\\s*["']?(?!\\*\\*\\*)[^\\s"'*][^\\r\\n"']*`, 'gi'), '$1: ***'],
  [/\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/g, '***'],
  [new RegExp(`\\b(?:${PROVEEDOR})`, 'g'), '***'],
  [/\b(Basic|Digest|Bearer|Token|NTLM|Negotiate)\s+(?!\*\*\*)[A-Za-z0-9._~+/=-]{8,}/gi, '$1 ***'],
  [new RegExp(`${INICIO}(${CLAVE}["']?\\s*[:=]\\s*["']?)(?!\\*\\*\\*)[^\\s"'&,;}]{4,}`, 'gi'), '$1***'],
  [/(\b[a-z][a-z0-9+.-]{0,30}:\/\/)[^/\s@]{1,400}@/gi, '$1***@'],
];

export function depura(texto: unknown, limite = MAX_TEXTO): string {
  return DEPURACION.reduce((t, [patron, reemplazo]) => t.replace(patron, reemplazo), String(texto)).slice(0, limite);
}

// Captura de texto del paso: lo anotado y, si un paso sin navegador falló, su error (aunque no anotara nada).
export function textoDelPaso(notas: string[], error: string | null, conNavegador: boolean): string | null {
  const lineas = [...notas, ...(error && !conNavegador ? [`ERROR: ${error}`] : [])];
  return lineas.length ? depura(lineas.join('\n'), MAX_CAPTURA_TEXTO) : null;
}

function limpiaParametros(params: URLSearchParams): void {
  for (const nombre of [...params.keys()]) {
    if (PARAMETRO_SENSIBLE.test(nombre)) params.set(nombre, '***');
  }
}

export function limpiaUrl(crudo: string): string {
  try {
    const url = new URL(crudo);
    if (url.username || url.password) { url.username = '***'; url.password = ''; }
    limpiaParametros(url.searchParams);
    if (url.hash.includes('=')) {
      const fragmento = new URLSearchParams(url.hash.slice(1));
      limpiaParametros(fragmento);
      url.hash = fragmento.toString();
    }
    return depura(url.toString());
  } catch {
    return depura(crudo);
  }
}

let repo: { raiz: string; head: string } | undefined;
function datosDelRepo(): { raiz: string; head: string } {
  if (!repo) {
    try {
      const git = (args: string) => execSync(`git ${args}`, { encoding: 'utf8' }).trim();
      repo = { raiz: git('rev-parse --show-toplevel'), head: git('rev-parse HEAD') };
    } catch {
      repo = { raiz: process.cwd(), head: '' };
    }
  }
  return repo;
}

function casoDe(titulo: string): string {
  const m = titulo.match(/\b(M-\d{2,})\b/);
  if (!m || !ID_CASO.test(m[1])) throw new Error(`El título «${titulo}» no lleva un ID de caso M-01: sin él no hay evidencia`);
  return m[1];
}

function escucha(page: Page, consola: Registro[], red: Registro[]): void {
  page.on('console', (m) => consola.push({ tipo: m.type(), texto: depura(m.text()) }));
  page.on('pageerror', (e) => consola.push({ tipo: 'pageerror', texto: depura(e.message) }));
  page.on('requestfailed', (r) =>
    red.push({ estado: r.failure()?.errorText ?? 'fallida', metodo: r.method(), url: limpiaUrl(r.url()) }));
  page.on('response', (r) => {
    if (r.status() >= 400) red.push({ estado: String(r.status()), metodo: r.request().method(), url: limpiaUrl(r.url()) });
  });
}

function escribeAtomico(ruta: string, datos: unknown): void {
  const temporal = `${ruta}.${process.pid}.tmp`;
  fs.writeFileSync(temporal, JSON.stringify(datos, null, 1));
  fs.renameSync(temporal, ruta);
}

function preparaDirectorio(raiz: string, caso: string, corrida: string | undefined, reintento: number): string {
  if (fs.existsSync(path.join(raiz, 'cruce.json'))) throw new Error('Esta vuelta ya se cruzó: corre la evidencia en una vuelta nueva');
  const dir = path.resolve(raiz, caso);
  if (path.dirname(dir) !== path.resolve(raiz)) throw new Error(`El caso «${caso}» sale de EVIDENCIA_DIR`);
  if (corrida && reintento > 0) throw new Error('La corrida de evidencia exige --retries=0: un reintento ocultaría la falla');
  const previo = path.join(dir, 'pasos.json');
  if (corrida && fs.existsSync(previo) && JSON.parse(fs.readFileSync(previo, 'utf8')).corrida === corrida) {
    throw new Error(`${caso} ya corrió en esta corrida (otro proyecto o --repeat-each): usa un solo proyecto`);
  }
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

async function capturaDePantalla(page: Page, dir: string, n: number, opciones: OpcionesPaso): Promise<string | null> {
  const captura = `paso-${String(n).padStart(2, '0')}.png`;
  let capturada = true;
  try {
    // getByText no ve el valor de un input o textarea: los que traen un secreto (o cuyo nombre dice que lo guardan)
    // se marcan para taparlos.
    await page.evaluate(MARCA_CAMPOS_SENSIBLES, [TOKEN_VISIBLE.source, NOMBRE_SENSIBLE.source] as [string, string])
      .catch(() => {});
    const mascara = [page.locator(SELECTOR_SENSIBLE), page.getByText(TOKEN_VISIBLE),
      page.locator('[data-evidencia-token]'), ...(opciones.mascara ?? [])];
    await page.screenshot({ path: path.join(dir, captura), fullPage: true, mask: mascara });
  } catch {
    capturada = false;
  }
  await page.evaluate(() => document.querySelectorAll('[data-evidencia-token]')
    .forEach((el) => el.removeAttribute('data-evidencia-token'))).catch(() => {});
  return capturada ? captura : null;
}

// Arma el `paso` de una prueba; sin página (pasoApi) la captura es solo el texto que el cuerpo anota.
async function conPasos(page: Page | null, testInfo: TestInfo, use: (paso: Paso) => Promise<void>): Promise<void> {
  const caso = casoDe(testInfo.title);
  const corrida = process.env.EVIDENCIA_CORRIDA;
  const dir = preparaDirectorio(process.env.EVIDENCIA_DIR || path.join('test-results', 'evidencia'), caso, corrida,
    testInfo.retry);
  const { raiz, head } = datosDelRepo();
  const consola: Registro[] = [];
  const red: Registro[] = [];
  const pasos: Record<string, unknown>[] = [];
  if (page) escucha(page, consola, red);

  const guarda = (estado: string | null) => escribeAtomico(path.join(dir, 'pasos.json'), {
    caso, titulo: depura(testInfo.title), archivo: path.relative(raiz, testInfo.file), head,
    proyecto: testInfo.project.name, corrida: corrida ?? null, reintento: testInfo.retry, estado, pasos,
    generado: new Date().toISOString(),
  });

  const paso: Paso = async (accion, esperado, cuerpo, opciones = {}) => {
    const n = pasos.length + 1;
    const desdeConsola = consola.length;
    const desdeRed = red.length;
    const inicio = Date.now();
    const notas: string[] = [];
    let resultado = 'falla';
    let error: string | null = null;
    try {
      await base.step(`${n}. ${accion}`, () => cuerpo((texto) => { notas.push(String(texto)); }));
      resultado = 'pasa';
    } catch (e) {
      error = depura((e as Error)?.message ?? e);
      throw e;
    } finally {
      const captura = page ? await capturaDePantalla(page, dir, n, opciones) : null;
      let texto: string | null = null;
      const contenido = textoDelPaso(notas, error, page !== null);
      if (contenido !== null) {
        texto = `paso-${String(n).padStart(2, '0')}.txt`;
        fs.writeFileSync(path.join(dir, texto), contenido);
      }
      pasos.push({
        n, accion: depura(accion), esperado: depura(esperado), resultado, error,
        url: page ? limpiaUrl(page.url()) : null, captura, texto, consola: consola.slice(desdeConsola),
        red: red.slice(desdeRed), duracion_ms: Date.now() - inicio,
      });
      guarda(null);
    }
  };

  await use(paso);
  guarda(testInfo.status ?? null);
}

export const test = base.extend<{ paso: Paso; pasoApi: Paso }>({
  paso: async ({ page }, use, testInfo) => conPasos(page, testInfo, use),
  // eslint-disable-next-line no-empty-pattern
  pasoApi: async ({}, use, testInfo) => conPasos(null, testInfo, use),
});

export { expect };
