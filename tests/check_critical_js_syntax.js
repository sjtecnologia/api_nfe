const fs = require('fs');
const vm = require('vm');
const path = require('path');

const files = [
  path.join(__dirname, '..', 'templates', 'admin', 'nfes', 'emitir.html'),
];

for (const file of files) {
  const html = fs.readFileSync(file, 'utf8');
  const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)];
  if (scripts.length === 0) {
    throw new Error(`Nenhum script inline encontrado em ${file}`);
  }

  scripts.forEach((match, index) => {
    const source = match[1]
      .replace(/\{\{[\s\S]*?\}\}/g, 'null')
      .replace(/\{%[\s\S]*?%\}/g, '')
      .trim();
    if (!source) return;
    try {
      new vm.Script(source, { filename: `${file}#script-${index + 1}` });
    } catch (error) {
      throw new Error(`${file}#script-${index + 1}: ${error.message}`);
    }
  });
}

process.stdout.write('JavaScript crítico: sintaxe válida\n');
