// Transpile the upstream adapter without altering the Awatif solver.
const { transform } = require('esbuild');
const fs = require('node:fs/promises');
const path = require('node:path');
async function build() {
  const source = path.join(__dirname, 'node_modules/awatif-fem/src');
  const destination = path.join(__dirname, 'dist/awatif');
  await fs.mkdir(path.join(destination, 'cpp/built'), { recursive: true });
  const { code } = await transform(await fs.readFile(path.join(source, 'deformCpp.ts'), 'utf8'), {
    loader: 'ts', format: 'esm', target: 'es2022',
  });
  await fs.writeFile(path.join(destination, 'deformCpp.js'), code);
  await fs.writeFile(path.join(destination, 'package.json'), '{"type":"module"}\n');
  for (const file of ['deform.js', 'deform.wasm']) {
    await fs.copyFile(path.join(source, 'cpp/built', file), path.join(destination, 'cpp/built', file));
  }
  console.log('Awatif WebAssembly solver prepared.');
}
build().catch(error => { console.error(error.message); process.exitCode = 1; });
