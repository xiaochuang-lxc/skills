# wawk/WAL 深入参考（wal_eh 仓库，全部结论经真实波形运行验证）

仓库：`/Users/feng/Desktop/Code/wal_eh`（WAL 0.9.1 + 四态扩展）。
wawk 源码：`wawk/parser.py`（文法）、`wawk/ast_defs.py`（转译）、`wawk/wawk.py`（CLI）。
WAL 标准库：`wal/libs/std/std.wal`；算子实现：`wal/implementation/`。

## 1. 执行模型

- 程序 = 若干 `function 名(参数) { ... }`、`BEGIN: { ... }`、`条件1, 条件2: { ... }`、`END: { ... }`。
- 转译结果：`(do 变量定义 BEGIN...) (whenever true (when (&& 条件...) 动作)...) END...`。
  即：**所有条件语句在波形每个索引处逐条求值**，不是边沿触发；BEGIN/END 各执行一次。
  whenever 结束后索引**恢复为循环前的值（通常是 0）**，END 里读 INDEX 不是最大索引。
- 恒真条件写 `INDEX >= 0:`，**不要写 `1:`**：AST 分类时 Python `[1] == [True]` 成立，
  误入函数定义分支报 `AttributeError: DEFUN`（已实测）；`0:` 作永不触发的哑语句是安全的。
- `INDEX`：当前索引（0 起，每个"有信号变化的时间戳"一个索引，同一时间戳的所有变化共享一个索引）。
  `TS`：当前仿真时间戳。`MAX-INDEX`：最大索引（wawk 中须 `eval(parse("MAX-INDEX"))`）。
- 变量：`x = expr;` 自动定义（转译期扫描所有赋值，预定义为 0）；`var x = expr;` 显式定义。
  数组：`a[k] = v;` 自动创建；读缺失键返回 0（转译为 `geta/default`）。键可以是 int/字符串/信号值。
- 语句必须以 `;` 结尾；块 `{}`；注释 `//`；字符串双引号。
- 函数无 `return`，值 = 块内最后一个表达式。`if (c) { a; } else { b; }` 是表达式。
- 循环：`for (x in xs) { ... }`、`for (k, v in arr) { ... }`、
  `for (i = 0; i < n; inc(i)) { ... }`（第三槽是**表达式**不是赋值，写 `i += 1` 解析错误；
  `inc(i)`/`dec(i)` 是标准库宏，已验证）。
- 复合赋值 `+= -= *= /=` 仅支持普通变量，**不支持 `a[k] += 1`**。

## 2. 符号与表达式文法（关键限制）

- 符号名只允许 `字母/数字/_/$/.`，可尾随一个 `?`。因此：
  - 可直接用：`rising falling stable unstable count sum filter sort reverse append signed`
    `print printf find case casez casex slice band bor bxor bnot x? z? known? signal? int?`
    `length first last rest in map fold range max min average zip type list eval parse`
    `import call step exit defined?` 等（完整算子表见 `wal/ast_defs.py` 的 `Operator`）。
  - `alias(d, tb.data)` 直接调用**失败**（第二参被求值成信号值）；用
    `eval(parse("(alias d \"tb.data\")"))`（已验证；VCD 下目标信号还需在程序中字面出现一次）。
  - **不能直接写**（含 `-` `/` `->`）：`MAX-INDEX SIGNALS-NO-ALIAS LOCAL-SIGNALS`
    `signal-width find/g fold/signal sample-at trim-trace convert/bin string->int bits->sint`
    `string->symbol symbol->string int->string set-scope all-scopes loaded-traces set-index` 等。
  - 通用绕法：`eval(parse("WAL 原文"))`，如
    `eval(parse("(signal-width 'tb.data)"))`、`eval(parse("(convert/bin tb.data)"))`、
    `eval(parse("(find/g (&& t0^valid t1^ready))"))`。
- `sig@N`：索引偏移 N 处求值（`reval`）。**越界返回 false**（不是报错），比较前用 `INDEX >= n` 守卫。
- `sig[3]` 取位、`sig[7:4]` 取切片（MSB:LSB，LSB 起编号）——只能用于信号，不能用于字面量/变量；
  值切片用函数 `slice(v, hi, lo)` / `slice(v, bit)`。
- `#name`：组内解析（`seval.group + name`），配合 `group([...]) { ... }`；组名**必须带尾点**。
  `groups("valid", "ready")` 返回同时含这些后缀的公共前缀列表（如 `("tb." "tb.dut.")`）。
- `~name` 与 `scope(name)` 在 wawk 中**损坏**（转译为参数数不符的 in-scope / 作用域符号被当变量求值），
  用完整层次名代替。WAL 原文里它们才正常。
- 运算符优先级陷阱：`!` 的操作数会贪婪延伸到整个后续表达式（含 `||`）：
  `!a || b` → `!(a || b)`；`!(a) || b` 仍是 `!(a || b)`。
  安全形式：`a == 0 || b`、`( !(a) ) || b`、`!x && y`（&& 链中安全）。
  怀疑优先级时一律 `wawk -o out.wal prog.wawk trace` 看转译结果。
- `==`/`!=` 转译为 WAL `=`/`!=`（逻辑相等）；`===`/`!==` 转译为 case equality。

## 3. 四态（0/1/x/z）语义

- 含 x/z 的信号值是四态值（LogicValue）；纯 0/1 值仍是整数。字面量 `0b1x0z`（`?`=`z`，大小写不敏感）；
  纯 `0b101` 是整数 5。
- `==`/`!=`/`>`/`<`/`!` 涉及 x/z → 结果未知 `1'bx`；未知值用作
  if/&&/||/while/find/whenever 的条件 → **立即 UnknownConditionError**，
  报错带信号名与 TS（例：`unknown value 'x' used as condition (signal tb.clk at TS 0)`）。
  求值短路：`0 && x值` 不报错，`1 && x值` 报错。
- `===`/`!==` 逐位精确比较，永远返回 bool：`tb.data === 0bxxxx`、`tb.data !== tb.data@-2`。
- 谓词（永远 bool，可安全作条件）：`x?(v)` 含 x、`z?(v)` 含 z、`known?(v)` 无 x/z。
- 位运算 `band/bor/bxor/bnot` 按 Verilog 真值表传播 x（z 按 x 处理）；`bnot(0b1x0z)=0b0x1x`。
  WAL 无位移算子；`~` 不是按位非。
- 算术任一操作数含 x/z → 全 x；`bits->sint`/`string->int`/`max`/`min`/`average` 等遇 x 报错。
- 打印：`print("v=", sig)`（逗号分隔）或 `printf("%s", sig)` 输出位串如 `1x0z`；
  `printf("%d", 四态值)` 报 TypeError；字符串 `+` 拼接遇 x 报错/传播。
- `case` 精确匹配（含 x 无匹配且无 default 报错）；`casez` z/? 通配；`casex` x/z 通配：
  `casex(tb.data, [0b1x0z, 1], [default, 0])`。
- x 定位工作流：`find(x?(sig))` 拿全部 x 索引 → 在首个 x 索引处检查驱动源
  （`sig@-1` 看前一时刻）→ 用 `known?` 守卫写 x 容忍分析。

## 4. 波形后端差异（重要）

| 行为 | FST | VCD/CSV |
|---|---|---|
| 依赖 | pylibfst（缺失时报 ModuleNotFoundError 并提示安装） | 无 |
| keep_signals 过滤 | **不过滤**，全部信号可读 | 只加载程序中**字面出现**的信号名 |
| `SIGNALS` 枚举 | 完整 | 仅程序引用过的信号（可能为空） |
| `#name`/动态拼接名 | 正常 | 需全名在程序某处字面出现一次 |
| from_string | 不支持 | 支持 |

- VCD 信号发现：`grep '\$var' trace.vcd`（层次由 `$scope` 给出，点号拼接）。
- 短向量按 VCD 左扩展规则补齐（首位 x/z 补 x/z，首位 0/1 补 0），FST/VCD 逐位一致
  （`examples/four-state/four_state.wawk` 在 xz.fst 与 xz.vcd 上输出已验证完全相同）。

## 5. Python API 与多波形

```python
# 用 /Library/Developer/CommandLineTools/usr/bin/python3（有 pylibfst），在仓库目录下
from wal.core import Wal
w = Wal()
w.load('examples/basics/counter.fst', 't0')     # tid 自定义
w.load('examples/four-state/xz.vcd', 't1')
w.eval_str('(loaded-traces)')                    # ['t0', 't1']
w.eval_str('t0^tb.dut.counter')                  # 多波形时用 tid^信号名
w.eval_str('(find t0^tb.dut.overflow)')          # [39, 40, 73, 74]
w.eval_str('t0^MAX-INDEX')                       # WAL 原文里连字符名字正常
```

- `w.eval_str` 单表达式；`w.run_str` 从索引 0 重跑；`w.eval_file('x.wal')`；
  `w.register_operator(name, fn)` 注册自定义算子。
- 多波形注意：`step`/`reval`/`@` 会同时推进**所有**波形；`find` 逐个波形单独步进，
  跨波形条件要用 `find/g`（全局同步步进，返回各波形索引的 dict 列表，已验证：
  `(find/g (&& t0^tb.dut.clk (x? t1^tb.data)))` → `[{'t0': 3, 't1': 3}, {'t0': 5, 't1': 5}]`）。
  单波形条件 + 多波形加载时 find 结果会失真，边沿统计建议单波形进行。
- wawk CLI 一次只加载一个波形（tid 固定 WAWK_TRACE）；多波形对比走 Python API。
- Python 互操作（wawk 内）：`import(extern);` 加载 cwd 下 extern.py，
  `call(extern.decode, sig)` 调函数；命令行尾参进入 `args` 列表。

## 6. 转译调试与常见错误速诊

| 症状 | 根因 | 处置 |
|---|---|---|
| `variable MAX is undefined` | `MAX-INDEX` 被解析为 `MAX - INDEX` | `eval(parse("MAX-INDEX"))` |
| `No terminal matches '='` | `a[k] += 1`，或 C 风格 for 的更新槽写了赋值 | `a[k] = a[k] + 1`；更新槽用 `inc(i)` |
| 解析错误指向 `return`/`->`/`/` | 文法不支持 | 末表达式返回值；`eval(parse(...))` |
| `whenever: expects exactly two arguments` | 程序只有 BEGIN/函数 | 加 `0: { }` |
| `AttributeError: DEFUN` | 条件写了 `1:`（`[1]==[True]` 误入函数分支） | 改 `INDEX >= 0:` |
| `UnknownConditionError ... (signal S at TS T)` | x/z 进入条件 | 守卫 `known?` 或改 `===`；这本身即 x 定位线索 |
| `resolve-group: No signal with name "tbdata"` | 组名缺尾点 | `group(["tb."])` |
| `variable tb.dut is undefined` | `scope(tb.dut)` | 用全名 |
| `scoped: exactly two arguments required` | wawk 的 `~sig` | 用全名 |
| `%d format: a number is required, not str` | printf %d 遇四态值 | 改 `%s` |
| `Cannot open file ... install "pylibfst"` | 解释器缺 pylibfst | 用 PATH 的 wawk 或 3.9 解释器 |
| 结果逻辑与预期不符但无报错 | `!` 优先级吞表达式 | `wawk -o` 看转译，改 `== 0` |

错误打印自身可能再抛 `TypeError: tuple indices must be integers`（line_info 格式 bug），
忽略次生异常，看首个 AssertionError/UnknownConditionError 的消息体。

## 7. 已验证示例索引

`examples/`（本 skill 目录）内每个 .wawk 头部注释给出运行命令与期望输出；
`handshake.vcd` 为自带测试波形（7 个时钟周期、含 x 数据段），可离线自检。
仓库侧参考：`examples/wawk/basics2.wawk`、`examples/wawk/vexriscv-pipeline/pipeline.wawk`
（group/# 与 HTML 报告）、`examples/four-state/four_state.wawk`（四态全家桶）、
`examples/advanced/axi-stream.wal`（WAL 原文的握手延迟分析原型）。