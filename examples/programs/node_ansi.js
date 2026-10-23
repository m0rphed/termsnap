const E = String.fromCharCode(27);
let line = "";
for (let i = 0; i < 48; i++) line += `${E}[48;5;${16 + i * 4}m `;
console.log(line + `${E}[0m`);
line = "";
for (let i = 0; i < 48; i++) line += `${E}[48;2;${i * 5};${255 - i * 5};160m `;
console.log(line + `${E}[0m`);
for (let step = 0; step <= 10; step++) {
  process.stdout.write(`\r${E}[32m[${"#".repeat(step)}${".".repeat(10 - step)}]${E}[0m ${step * 10}%`);
}
process.stdout.write(`\r${E}[2K${E}[1mГотово${E}[0m\n`);
console.log(`${E}[1;4;31mжирный подчёркнутый красный${E}[0m ${E}[3;33mкурсив жёлтый${E}[0m ${E}[90mсерый${E}[0m ${E}[94;103mъяркие${E}[0m`);
console.log(`${E}]0;заголовок окна\x07${E}[?25lскрытый курсор${E}[?25h`);
