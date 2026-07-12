.. _cookbook-index-base:

Cookbook: adopting ``index_base`` / ``index_region``
====================================================

:meth:`~dasmos.Disassembler.index_base` and
:meth:`~dasmos.Disassembler.index_region` fix a real defect — a table
indexed by a key no longer masquerades on the memory map as a single
owned byte with phantom reads and writes (see
:ref:`indexed-base-addresses` for the API, and the reference-kinds memo
in ``docs/design/reference-kinds-memo.md`` for the *why*). But they are
*annotation-only*: they never change emitted bytes, so ``verify``
passing tells you nothing about whether a conversion was *correct*.
Correctness comes from one habit:

   **Read the label and its usage in context before converting it.** The
   tooling finds candidates; only the code tells you what a label
   actually is.

This how-to is the workflow and judgement for retrofitting these calls
onto a real, already-annotated driver — distilled from migrating a
full multi-version 6502 disassembly (Acorn NFS/ANFS, 11 ROMs) to
dasmos 2.0: roughly 480 ``index_base`` conversions, plus a careful
decision *not* to use ``index_region`` anywhere in that codebase.


1. Sequence the work
--------------------

Do the bare version bump on its own first — regenerate, and confirm
``verify`` still passes **byte-identically** and only cross-reference
*prose* changed. dasmos 2.0 is annotation / JSON-shape only; if bytes
move, stop and investigate before editing anything. Commit that clean
upgrade separately, then start converting on a known-good baseline.

If you have local tooling that parses the output JSON, note the schema
is now versioned: ``references`` entries are ``{addr, kind, move_id?}``
objects, and each ``memory_map`` row's ``access`` is an ordered
``["r", "w", "b"]`` array — a base is a row carrying ``"b"`` (schema v4;
earlier dasmos used a separate ``index_bases`` array).


2. Find candidates — as leads, not as an oracle
-----------------------------------------------

A **pure** index base shows in the ``.asm`` cross-reference as ``used as
index base N times`` with *no* ``referenced``. A **mixed** address
(``referenced … also used as index base …``) is touched both ways —
leave it a plain :meth:`~dasmos.Disassembler.label`. In the JSON, pure
bases you have already declared show as ``memory_map`` rows whose
``access`` is ``["b"]``; ``references[].kind`` gives you the split
programmatically.

Two blind spots to compensate for:

- **Low-page (zero-page / page 0–2) bases are under-reported in the
  JSON.** The ``.asm`` cross-reference *does* classify them (``used as
  index base``), but the JSON ``references[].kind`` currently does not
  carry the kind for those targets — so anything built on the JSON
  (including orchestration CLIs) will miss them. Trust the ``.asm``
  there.

- **Relocated-code entries masquerade as pure data bases.** A block
  copied to RAM by :meth:`~dasmos.Disassembler.add_move` has its code
  items at the *source* address; the destination entry point therefore
  has no local ``code`` item, and its copy loop writes it as
  ``sta dest,Y`` — which looks exactly like an index base. **Always
  also exclude** :meth:`~dasmos.Disassembler.entry` **targets and move
  destinations.** Converting one moves a live entry point off the map —
  the cardinal error this feature must not cause.

Orchestration tools can list the pure set for you (for example
fantasm's ``labels list --index-base-only``, which also flags
``type=='code'`` items). Treat their output as a worklist to *read*,
never as a batch to convert.


3. Decide per label, by reading
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - You're looking at…
     - Do
   * - a :meth:`~dasmos.Disassembler.label` **data** base — RAM/ZP
       scratch *or* a ROM table / template / offsets / lookup, only ever
       ``lda`` / ``sta …,X`` / ``,Y``
     - **Convert** to ``index_base``, keeping ``description`` / ``group``
       / ``length``; drop any ``access=`` (``index_base`` asserts the
       ``b`` flag itself, and a pure base has no ``r`` / ``w``).
   * - any ``type=='code'`` item, or an
       :meth:`~dasmos.Disassembler.entry` / move destination
     - **Leave** — code label (the caveat).
   * - a :meth:`~dasmos.Disassembler.subroutine`-style **data banner** (a
       documented data region with a title / structure)
     - **Leave** — it isn't a ``label()``; converting strips the banner,
       and its cross-reference already reads correctly.
   * - an **auto-generated** (``l####``) or **environment** label
     - **Leave** — no ``label()`` to convert, no value as a base.

The name usually gives the class away — *table / template / offsets /
strings / lookup* is data; *entry / handler / start / a jmp-or-branch
target* is code — but when name and usage disagree, trust the usage. A
``…_entry`` that is only ever read as ``lda …,X`` to scan a header is a
data base; a ``…_table`` that is jumped into is not. Read the inline
comments you already wrote: they usually say which.

A throwaway script that rewrites ``label(`` → ``index_base(`` over a
**curated** address set (dropping ``access=``, handling multi-line
calls) saves tedium — but the set must come from your reading, never
straight from a tool. Afterwards, re-run ``verify`` and your linter, and
assert that **no** :meth:`~dasmos.Disassembler.entry` **target became an
index_base** in any driver. ``verify`` passing proves you did not change
bytes; it does *not* prove the classification is right.


4. ``index_region``: use it only where it earns its place
---------------------------------------------------------

:meth:`~dasmos.Disassembler.index_region` renders in-window neighbours
as ``anchor±k,X``, so you do not hand-write a label per slot. Its payoff
is **eliminating tedious per-slot labels for mechanically-related
notional slots** around a real anchor — the free-space-map-scratch case
in the API docs.

Do **not** reach for it just because addresses are close. Most
"clusters" are the opposite of its use case, and a region makes them
*worse*:

- **lo/hi address-table pairs** (``*_lo`` / ``*_hi``): the names carry
  the meaning; ``anchor+k,X`` buries it. Keep two ``index_base``\ s.
- **distinct adjacent tables** that merely abut: different data →
  different names.
- **N-byte-spaced parallel arrays** (one column per field, shared
  index): each is its own documented array, not a slot.
- **single base-adjustment tricks** (a base chosen so ``base+Y`` lands
  in another region, often already carrying an explanatory comment): one
  meaningful base, not a swept range — a region flattens the arithmetic
  and discards the comment.

Rule of thumb: if you would otherwise be forced to hand-name many
*interchangeable* slots, a region helps. If each address has a distinct
role and a comment explaining it, **naming beats arithmetic** — leave
them as ``index_base``. Decide by reading the usages, not by address
spacing. (Region windows must be disjoint; an explicit
:meth:`~dasmos.Disassembler.label` inside a window still wins.)


5. Wrap up
----------

Re-run ``lint`` / ``verify`` across every version (clean and
byte-identical). Spot-check the JSON: converted addresses should sit in
``memory_map`` with ``access`` containing ``"b"`` (a ``["b"]``-only row
for a pure base). Commit the conversions
separately from the bare upgrade, and record the data-vs-code / banner /
auto-label rules and the "don't force ``index_region``" guidance in your
project's own notes so the next pass stays consistent.
