# ritual

A hobby combat simulator for Wizard101, written by hand.

## Why this exists

Wizard101's combat engine is extraordinarily complicated. Damage, resist, pierce, crit
curves, charms, wards, auras, HOT/DOT, pips, hanging effects, split damage, and most of
all, cheats.

This project is an attempt to recreate that logic so that both

## AI policy

This is not an anti-AI project, and nobody is being punished for using AI. The rule is narrow:

- **The package implementation is written by hand.** Simulation logic, effect handling, state
  and data-model classes, loaders and adapters, and the package's tests are not generated.
- **AI help is welcome for everything around that:**
  - exploring how the game's data is organized and what its fields mean;
  - digging through huge files (counting, searching, summarizing);
  - building throwaway exploration tools;
  - discussing design: architecture, tradeoffs, risks, reviewing ideas;
  - explaining mechanics, or explaining what is wrong in code you wrote.
- **Short illustrative snippets** (a handful of lines) are fine. Drop-in functions or modules
  are not.
- **The one exception is generated type scaffolding.** The enums and dataclasses in
  `src/ritual/types` are produced mechanically by `generate_base_types.py` from the game's own
  type definitions. They are not hand-edited. When the game updates, regenerate them.
  Don't blindly replace them, however. Look at the changes and determine what to do.

A simple test: if all AI-written code were deleted, **except the generated type scaffolding**,
the package would still work. Nothing in `scripts/` is load-bearing; those tools help a human
understand the data, and the package never imports them or uses their output.

AI-written scripts say so in a header. See `scripts/generate_base_types.py` for the format.
Agents working in this repo are told the same rules in [`AGENTS.md`](AGENTS.md).

## Repository layout

| Path | What it is |
|---|---|
| `src/ritual/` | The package. Hand-written, except for `types/`. |
| `src/ritual/types/` | Generated enums and dataclasses. Generally not edited by hand. |
| `generate_base_types.py` | Regenerates `src/ritual/types` from a type dump. |
| `scripts/` | Optional exploration tools. Not used by the package. |
| `AGENTS.md` | Rules for AI agents working in this repo. |


## Getting started

### 1. Bring your own type dump

The game's type definitions are not included in this repository, because they could reasonably
be considered proprietary data. You generate your own with
[wiztype](https://github.com/wizwalker/wiztype) while the Wizard101 client is running; the
[katsuba README](https://github.com/vbe0201/katsuba) explains the setup. Place the result at
`assets/` so it's automatically gitignored. (or wherever your tools expect it).

Never commit the dump, or decoded game data, to this repository.

### 2. Generate the types

```
python generate_base_types.py <dump.json> <outdir>
```

Check the script's docstring for the current arguments. Rerun it whenever the game updates,
and read the `git diff` of `src/ritual/types` to see what changed if anything.
If something did, there's work to be done!

### 3. Decode game data for reading

Template data is loaded with [katsuba](https://github.com/vbe0201/katsuba). To browse game
files yourself, `scripts/decode-op-folder` takes a nested folder of serialized objects and
writes readable JSON to a parallel `-decoded` folder. It is a convenience for humans only.
The package does not use its output. In fact they get mangled in the process of making
them easier to read anyway.

## Status

Serene's in decision paralysis for the basic setups. Try again later.

## Contributing

Issues and design discussion are welcome. For code contributions to the package itself, please
write them yourself. That is the premise of the project, and contributions that are clearly
generated will be declined. Exploration tooling and documentation fixes are fine, with AI use
disclosed in the file header as described above.

## License

MIT, with additional restrictions.

1. The Software and any modifications made to it may not be used for the purpose of training or improving machine learning algorithms,
including but not limited to artificial intelligence, natural language processing, or data mining. This condition applies to any derivatives,
modifications, or updates based on the Software code. Any usage of the Software in an AI-training dataset is considered a breach of this License.

2. The Software may not be included in any dataset used for training or improving machine learning algorithms,
including but not limited to artificial intelligence, natural language processing, or data mining.

3. Any person or organization found to be in violation of these restrictions will be subject to legal action and may be held liable
for any damages resulting from such use.

In short, humans did the work. Models should stop training on it without permission.
