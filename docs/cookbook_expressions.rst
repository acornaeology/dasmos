.. _cookbook-expressions:

Cookbook: expressions and macros
================================

Everywhere a driver supplies a value that isn't a plain label or number
— a byte pulled from an address, a masked offset, a computed table entry
— it uses an *assembler-neutral expression*. dasmos renders that one
expression into whichever assembler you target: beebasm's ``&`` hex and
``AND`` keyword, 64tass's ``$`` and ``&``, each with the parentheses that
*that* assembler's operator precedence requires. When the same shaped
expression recurs across a table, you can lift it into a *macro* — and
dasmos emits a real macro definition and invocations, in each backend's
own macro construct.

This cookbook builds up from a one-liner to the BBC BASIC inline-
assembler mnemonic-hash tables, which exercise the whole system. Every
rendered listing shown here is real output; every expression assembles
back to the original bytes on both beebasm and 64tass.

The DSL lives in :mod:`dasmos.expr`:

.. code-block:: python

   from dasmos.expr import ref, sym, lo, hi, hexlit, char, string, param

.. note::

   ``ir.render("beebasm")`` returns a
   :class:`~dasmos.output.TextOutput`, not a bare string — wrap it in
   ``str(...)`` (or ``print``) to get the source text:
   ``print(str(ir.render("beebasm")))``. The listings below are that
   string.


Recipe 1: an operand plus a constant
------------------------------------

The simplest case — an immediate operand that reads better as
``constant + 1`` than as a magic number. ``d.expr`` takes the **operand
byte** address (one past the opcode on the 6502):

.. code-block:: python

   d.constant(3, "num_lives")
   d.expr(0x8001, sym("num_lives") + 1)

Both backends render the same thing (the constant name is already valid
in either), so this is indistinguishable from hand-written source:

.. code-block:: text

   lda #num_lives + 1

``sym(name)`` is a bare symbolic name emitted verbatim. Use it for a
constant or any name you've defined elsewhere. A plain Python ``int``
on the other side of the ``+`` becomes a literal automatically.


Recipe 2: the low byte of a label, minus one
--------------------------------------------

The classic jump-table idiom: a byte table holding ``target-1`` low
bytes, pushed for an ``RTS`` dispatch. ``ref(addr)`` references the label
at a runtime address and resolves to its *name* at render time — so it
stays symbolic even if you name the target later in the driver:

.. code-block:: python

   d.label(0x8130, "dispatch_table")
   d.expr(0x8005, lo(ref(0x8130) - 1))

Renders (identically on both backends, since ``<(...)`` is common
syntax):

.. code-block:: text

   lda #<(dispatch_table - 1)

``hi`` is the high-byte counterpart. Note you did not write any
parentheses or a byte-select operator — ``lo`` and the subtraction are
*intent*; the renderer supplies ``<(...)`` for beebasm and 64tass (and
would supply ``LO(...)`` or ``>x`` for an assembler that spells it
differently).

.. tip::

   :meth:`~dasmos.Disassembler.code_ptr` and
   :meth:`~dasmos.Disassembler.rts_code_ptr` build these ``lo``/``hi`` of
   ``target-1`` trees for you from a pair of table addresses — reach for
   the DSL directly only when the pattern is irregular.


Recipe 3: a masked difference of two labels
-------------------------------------------

A table whose bytes are offsets *between* two labels, masked to a byte —
common in string tables where an entry records "distance from the base".
Python's operators compose the tree; ``&`` is bitwise-AND:

.. code-block:: python

   d.label(0x9000, "cmd_syntax_strings")
   d.label(0x9040, "syn_opt_dir")
   d.byte(0x9041, 1)
   d.expr(0x9041, (ref(0x9040) - ref(0x9000)) & 0xFF)

The interesting part is what dasmos does *not* emit — redundant
parentheses. ``AND``/``&`` binds looser than ``-`` in both assemblers, so
the subtraction needs no wrapping, and the value is still correct:

.. code-block:: text

   ; beebasm
   equb syn_opt_dir - cmd_syntax_strings AND &ff

   ; 64tass
   .byte syn_opt_dir - cmd_syntax_strings & $ff

If you *want* the grouping kept for readability, wrap it explicitly with
``group(...)`` (from :mod:`dasmos.expr`) and it renders with the
parentheses on every backend.


Recipe 4: forcing radix and character literals
----------------------------------------------

By default an integer renders with a small-int heuristic (``0``–``9``
decimal, larger values hex). Override per literal when the intent
matters:

.. code-block:: python

   from dasmos.expr import hexlit, declit, char

   hexlit(0x1F)     # &1f  / $1f
   declit(128)      # 128  (not &80)
   char(ord("A"))   # 'A'

``char`` is the expression-level equivalent of
:meth:`~dasmos.Disassembler.char_literal`; use it inside a larger
expression, and the sugar method for a standalone operand byte.


Recipe 5: string operations — keep the meaning visible
------------------------------------------------------

Some tables are *computed from text*. The canonical case is BBC BASIC's
inline assembler, whose mnemonic tables store a 15-bit "packed name" hash
of each mnemonic — the low five bits of each of its three letters, packed
together — split across a low-byte and a high-byte table.

You *could* spell the hash with three character literals. But dasmos has
string expressions, so you can write it in terms of the mnemonic string
itself — and, by default, the string stays visible in the disassembly,
because a listing exists to be read:

.. code-block:: python

   from dasmos.expr import string, group

   def hash_lo(mnemonic):
       s = string(mnemonic)
       key = (s[0] & 0x1F) * 0x400 + (s[1] & 0x1F) * 0x20 + (s[2] & 0x1F)
       return group(key) & 0xFF

   d.label(0x8450, "asm_mnemonic_lo")
   d.byte(0x8450, len(MNEMONICS))
   for i, mnemonic in enumerate(MNEMONICS):
       d.expr(0x8450 + i, hash_lo(mnemonic))

``string(m)[i]`` indexes the string; on a backend with native string
indexing the mnemonic is right there in the output:

.. code-block:: text

   ; 64tass — "LDA" indexed natively
   .byte (("LDA"[0] & $1f) * $0400 + ("LDA"[1] & $1f) * $20 + ("LDA"[2] & $1f)) & $ff

   ; beebasm — via ASC(MID$(...)), still showing the string
   equb ((ASC(MID$("LDA", 1, 1)) AND &1f) * &0400 + ...) AND &ff

Both assemble to the same hash byte (``&81`` for ``LDA``). String
slicing (``string("BRK")[0:2]``) and length (``str_len(...)``) are
available too.

**Readability vs terseness.** If you would rather the table read as bare
values, ask the renderer to fold constant string operations:

.. code-block:: python

   from dasmos.ext.renderers.beebasm import BeebasmRenderer
   ir.render(BeebasmRenderer(fold_string_ops=True))

which collapses ``"LDA"[0]`` to the character literal ``'L'``:

.. code-block:: text

   equb (('L' AND &1f) * &0400 + ('D' AND &1f) * &20 + ('A' AND &1f)) AND &ff

Folding is also the automatic fallback for an assembler that has no
string operations at all — the value is still emitted, just without the
string. The default, though, is to show the string.


Recipe 6: lift a repeated expression into a macro
-------------------------------------------------

Recipe 5 emits the *whole* hash expression on every table entry — correct,
but the listing is a wall of arithmetic. When the same shaped expression
recurs, define it **once** as a macro and invoke it per entry.
:meth:`~dasmos.Disassembler.define_macro` takes a name, parameter names,
and a body built with :func:`~dasmos.expr.param` placeholders; it returns
a callable that builds invocations:

.. code-block:: python

   from dasmos.expr import param, group

   m = param("mnem")
   pack_lo = d.define_macro("pack_lo", ["mnem"],
       group((m[0] & 0x1F) * 0x400 + (m[1] & 0x1F) * 0x20 + (m[2] & 0x1F)) & 0xFF)

   d.label(0x8450, "asm_mnemonic_lo")
   d.byte(0x8450, len(MNEMONICS))
   for i, mnemonic in enumerate(MNEMONICS):
       d.expr(0x8450 + i, pack_lo(mnemonic))

Now the shape is written once and each entry reads as ``pack_lo("LDA")``.
The two shipped backends differ in *how* a macro can be used, and dasmos
renders each in its native form.

**64tass** has value-returning functions, so the macro is a
``.sfunction`` and each invocation is a value used inline in the data
directive:

.. code-block:: text

   pack_lo .sfunction mnem, ((mnem[0] & $1f) * $0400 + (mnem[1] & $1f) * $20 + (mnem[2] & $1f)) & $ff

       .byte pack_lo("LDA"), pack_lo("STA"), pack_lo("BRK")

**beebasm** has no value function, so the macro is a code macro that
*emits* the byte, and each invocation is its own statement line:

.. code-block:: text

   MACRO pack_lo mnem
       equb ((ASC(MID$(mnem, 1, 1)) AND &1f) * &0400 + (ASC(MID$(mnem, 2, 1)) AND &1f) * &20 + (ASC(MID$(mnem, 3, 1)) AND &1f)) AND &ff
   ENDMACRO

       pack_lo "LDA"
       pack_lo "STA"
       pack_lo "BRK"

Both assemble to the identical table bytes. You wrote one macro; dasmos
chose the value-function form or the emit-a-line form according to what
the target assembler supports. The ``emit`` keyword
(``define_macro(..., emit="word")``) tells the statement-style backends
which data directive to emit — ``EQUB`` vs ``EQUW`` — for a word-valued
macro.


All the operators
-----------------

Expressions compose with Python's own operators (plus a few named
builders). Every one below renders to each backend's native token and is
verified to assemble to the same value on beebasm and 64tass.

.. list-table:: Binary operators
   :header-rows: 1
   :widths: 18 34 24 24

   * - DSL / Python
     - Meaning
     - beebasm
     - 64tass
   * - ``a + b``
     - addition
     - ``a + b``
     - ``a + b``
   * - ``a - b``
     - subtraction
     - ``a - b``
     - ``a - b``
   * - ``a * b``
     - multiplication
     - ``a * b``
     - ``a * b``
   * - ``a // b``
     - **integer** division
     - ``a DIV b``
     - ``a / b``
   * - ``a % b``
     - modulo
     - ``a MOD b``
     - ``a % b``
   * - ``a & b``
     - bitwise AND
     - ``a AND b``
     - ``a & b``
   * - ``a | b``
     - bitwise OR
     - ``a OR b``
     - ``a | b``
   * - ``a ^ b``
     - bitwise XOR
     - ``a EOR b``
     - ``a ^ b``
   * - ``a << b``
     - shift left
     - ``a << b``
     - ``a << b``
   * - ``a >> b``
     - shift right
     - ``a >> b``
     - ``a >> b``

.. list-table:: Unary operators and byte-selects
   :header-rows: 1
   :widths: 18 34 24 24

   * - DSL / Python
     - Meaning
     - beebasm
     - 64tass
   * - ``-a``
     - negation
     - ``-a``
     - ``-a``
   * - ``+a``
     - unary plus
     - ``+a``
     - ``+a``
   * - ``~a``
     - bitwise complement
     - ``NOT(a)``
     - ``~a``
   * - ``lo(a)``
     - low byte
     - ``<(a)``
     - ``<(a)``
   * - ``hi(a)``
     - high byte
     - ``>(a)``
     - ``>(a)``

String operations (the string-operations recipe above) round out the
set: index ``string(s)[i]``, slice ``string(s)[i:j]``, and
``str_len(string(s))``.

Two gotchas worth internalising:

- **Use** ``//`` **for division, never** ``/``. In the DSL ``//`` is
  integer division (what a 6502 assembler does); Python's ``/`` is float
  division and is rejected. ``//`` renders ``DIV`` on beebasm, ``/`` on
  64tass — the *same* integer operation, spelled each assembler's way.
- **Parenthesise bitwise masks.** Python's ``&`` / ``|`` / ``^`` bind
  *looser* than ``+`` and ``*``, so ``a + b & 0xFF`` means
  ``a + (b & 0xFF)`` in Python. Write ``(a + b) & 0xFF`` (or wrap the sum
  in :func:`~dasmos.expr.group`) when you mean "mask the whole thing" —
  the mnemonic-hash recipes do exactly this.

(``~`` maps to a bitwise-complement that beebasm has no operator for, so
it renders as beebasm's ``NOT(...)`` function — one example of dasmos
choosing each assembler's real spelling for you. A 65816 bank-byte
operator exists in the model but has no 6502 rendering.)


How it renders correctly everywhere
-----------------------------------

Two properties do the heavy lifting, and they're worth understanding
because they're *why* one expression can target many assemblers:

- **Precedence-aware parentheses.** beebasm and 64tass rank operators
  differently (beebasm's ``AND`` sits below ``+``; 64tass follows C).
  dasmos parenthesises against *each backend's* table, emitting the
  minimum needed for the value to be correct there. You never manage
  parentheses for portability.

- **Hex sigils, operator tokens, and byte-select spelling** are
  per-backend choices, not something the driver encodes — see the
  operator table above. The one expression means ``AND`` on beebasm and
  ``&`` on 64tass, ``DIV`` versus ``/`` for integer division, and so on.

The structured form is also available to non-assembler consumers: the
JSON renderer emits every expression as ``{"text": ..., "tree": ...}`` —
a ready rendering plus a walkable tree — and macros as a top-level
``macros`` section. A downstream tool can re-render to any syntax or
evaluate the expression itself.


Reaching further
----------------

The four assemblers dasmos knows about differ most in their macro
models: 64tass has value functions and native string indexing; beebasm
has code macros and ``MID$``/``ASC`` string functions but no value
function; ca65 imitates a value function with ``.define`` and indexes
with ``.strat``; acme has neither. dasmos ships beebasm and 64tass today;
the design that lets one macro render across all four — native construct
where available, graceful degradation where not — is written up in
``docs/design/expression-system.md`` (see decisions D-026 and D-027).
