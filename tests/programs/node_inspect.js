const util = require("node:util");
const data = {
  name: "Хованов",
  age: 21,
  active: true,
  nothing: null,
  missing: undefined,
  tags: ["a", "b", 3, Symbol("s")],
  nested: { deep: { deeper: { deepest: [1, 2, 3] } } },
  fn() {},
  date: new Date(0),
  map: new Map([["k", { v: 1 }]]),
  big: 12345678901234567890n,
};
console.log(data);
console.log(util.inspect(data, { colors: true, depth: 0 }));
console.log("%s=%d %o", "строка", 42, { x: 1 });
// без трассировки: ее строки содержат пути и внутренности Node, разные на каждой машине и в каждой версии
const failure = new TypeError("что-то пошло не так");
failure.stack = `${failure.name}: ${failure.message}`;
console.error(failure);
