#!/usr/bin/env python3
"""Extract combat-related reflection types from a wiztype-style JSON dump
into Python (IntEnum constants + dataclasses) and a trimmed JSON subset.
Usage: generate.py <dump.json> <outdir>

Disclaimer: Used as a development aid. LLM generated"""
import json, re, sys, os, keyword, collections

SRC = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/uploads/1791753077874_defaults-no-windows.json'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/mnt/user-data/outputs/wiz_combat'
raw = json.load(open(SRC))['classes']

# ---------------------------------------------------------------- indexing
def strip(n): return re.sub(r'^(class|struct|enum) ', '', n).rstrip('*')
C = {}
for v in raw.values():
    n = v['name']
    if n.endswith('*') or 'SharedPointer<' in n or n.startswith(('class std::', 'struct std::')): continue
    C[strip(n)] = v
def refs(t):
    return [m.group(1) for m in re.finditer(r'(?:class|struct|enum) ([\w:]+)', t)
            if not m.group(1).startswith('std::') and m.group(1) != 'SharedPointer']
subs = {}
for n, v in C.items():
    for b in v['bases']: subs.setdefault(b, []).append(n)

# ---------------------------------------------------------------- closure
ROOTS = """Spell SpellTemplate SpellEffect SpellEffectParamOverride SpellEffectPenalty SpellSubEffectMetadata SpellRank
ConditionalSpellEffectRequirement SpellFusionTemplate SpellIngredient MagicSchoolTemplate MagicSchoolInfo
CombatAction CombatResult CombatParticipant CombatResolver CombatRule CombatTriggerDescription TargetCritHit
Duel DuelModifier DuelModifierTemplate ShadowPipRule ShadowSpellTrackingData ParticipantPipData PipCount
PipConversionValues PipConversionLevelData ModifyPipRoundRateData WizardStatTable
GameEffectBase GameEffectTemplate GameEffectInfo GameEffectContainer
StartingPipEffect StartingPipEffectInfo StartingPipEffectTemplate TempStartingPipEffect TempStartingPipEffectInfo TempStartingPipEffectTemplate
SummonMinionEffect SummonMinionEffectInfo SummonMinionEffectTemplate
ProvideCombatTrigger ProvideCombatTriggerInfo ProvideCombatTriggerTemplate
ProvideSpellEffect ProvideSpellEffectInfo ProvideSpellEffectTemplate
StatisticEffect StatisticEffectInfo StatisticEffectTemplate
WizStatisticEffect WizStatisticEffectConfig WizStatisticEffectTemplate WizStatisticOverrideEffect WizStatisticOverrideEffectTemplate
WizStatisticScalerEffect WizStatisticScalerEffectTemplate WizDisableItemStatEffect WizDisableItemStatEffectTemplate
PolymorphEffect PolymorphEffectInfo PolymorphEffectTemplate
kDuelExecutionOrder kDuelPhase kShadow_Threshold_Type MinionType
BehaviorTemplate NPCBehaviorTemplate DuelistBehaviorTemplate DeckBehaviorTemplate SpellbookBehaviorTemplate
EquipmentBehaviorTemplate EquippedItemInfo DeckTemplate TieredSpellTemplate WizPolymorphTemplate
GameObjectTemplate WizGameObjectTemplate ItemTemplate WizItemTemplate ItemSetBonusTemplate ItemSetBonusData
EquipmentTemplate CombatSigilTemplate SigilTemplate SigilSubCircle""".split()
POLY = ['SpellEffect', 'CombatRule', 'ConditionalSpellEffectRequirement']   # pull in all subclasses
BLOCK = re.compile(r'Behavior|Cinematic|Derby|Window|Gui|Control|Widget|^Client|Quest|Pet|Housing|Template$|Info$|Sigil|Reward|Loot|Zone|Raid|Tutorial|Battleground|Fish|Elixir|Camera|Sound|Nif|^Obj|Path|Move|Anim', re.I)
STUB_ALWAYS = {'ResultList','AvatarItemInfoBase'}
ALLOW = set(ROOTS) | {'SpellTemplate','DuelModifierTemplate','SpellFusionTemplate','MagicSchoolTemplate','MagicSchoolInfo'}

inc, stubs, q = set(), set(), list(ROOTS)
while q:
    n = q.pop()
    if n in inc: continue
    if n not in C: stubs.add(n); continue
    inc.add(n); v = C[n]
    q += [b for b in v['bases'] if b != 'PropertyClass']
    if n in POLY: q += subs.get(n, [])
    for p in v['properties'].values():
        for r in refs(p['type']):
            if r in STUB_ALWAYS: stubs.add(r)
            elif r in ALLOW or not BLOCK.search(r): q.append(r)
            else: stubs.add(r)

# ---------------------------------------------------------------- enums
# enum definitions only exist as enum_options on property usages anywhere in the dump
ENUM = {}; conflicts = []
def _norm(k): return k.rsplit('::', 1)[-1]          # some usages qualify members as "Enum::kFoo"
for v in raw.values():
    for p in v['properties'].values():
        t = p['type']
        if t.startswith('enum ') and 'enum_options' in p:
            e = ENUM.setdefault(t[5:], {})
            for k, x in p['enum_options'].items():
                if not isinstance(x, int): continue
                k = _norm(k)
                if k in e and e[k] != x: conflicts.append((t[5:], k, e[k], x))
                e[k] = x
used_enums = {n for n in inc if C[n]['name'].startswith('enum ')}
for n in list(inc):
    for p in C[n]['properties'].values():
        for r in refs(p['type']):
            if p['type'].startswith('enum '): used_enums.add(r)
used_enums |= {n for n in inc if n in ENUM}
missing_enum = sorted(e for e in used_enums if e not in ENUM)
# stub-only enums that are referenced but blocked
for s in list(stubs):
    if s in ENUM: used_enums.add(s); stubs.discard(s)
classes = sorted(n for n in inc if C[n]['name'].startswith(('class', 'struct')))

# ---------------------------------------------------------------- naming
def pyname(n): return re.sub(r'\W', '_', n.replace('::', '_'))
def ident(s):
    s = re.sub(r'\W', '_', s)
    if s[0].isdigit() or keyword.iskeyword(s): s = '_' + s
    return s

INT = {'int','unsigned int','short','unsigned short','char','unsigned char','unsigned __int64','__int64','long','unsigned long','gid','s24','u24'}
def base_py(t, ctx):
    if t in ('std::string', 'std::wstring'): return 'str', '""'
    if t in ('float', 'double'): return 'float', '0.0'
    if t == 'bool': return 'bool', 'False'
    if t in INT or re.fullmatch(r'bui\d+', t) or t == 'wchar_t': return 'int', '0'
    if t.startswith('enum '): return pyname(t[5:]), None
    rs = refs(t)                      # unwraps SharedPointer<>/std::list<> to the element class
    if rs: return pyname(rs[0]), None
    return 'Any', 'None'

# ---------------------------------------------------------------- emit enums
os.makedirs(OUT, exist_ok=True)
L = ['"""Combat-related enum constants extracted from the Wizard101 reflection dump.',
     'Auto-generated by generate.py - do not edit by hand."""',
     'from enum import IntEnum', '']
ENUM_PY = {}
for n in sorted(used_enums):
    if n not in ENUM: continue
    pn = pyname(n); ENUM_PY[n] = pn
    L += [f'class {pn}(IntEnum):', f'    """enum {n}"""']
    seen = {}
    for k, x in sorted(ENUM[n].items(), key=lambda kv: (kv[1], kv[0])):
        i = ident(k)
        while i in seen: i += '_'
        seen[i] = x; L.append(f'    {i} = {x}')
    if not ENUM[n]: L.append('    pass')
    L.append('')
L += ['ENUMS = {' ] + [f'    {n!r}: {pn},' for n, pn in ENUM_PY.items()] + ['}', '']
open(f'{OUT}/enums.py', 'w').write('\n'.join(L))

# ---------------------------------------------------------------- emit types
def own_props(n):
    v = C[n]; par = next((b for b in v['bases'] if b != 'PropertyClass' and b in C), None)
    inherited = set(C[par]['properties']) if par else set()
    return par, {k: p for k, p in v['properties'].items() if k not in inherited}

def order(names):             # parents before children
    done, out = set(), []
    def visit(n):
        if n in done: return
        done.add(n)
        par = next((b for b in C[n]['bases'] if b != 'PropertyClass' and b in names), None)
        if par: visit(par)
        out.append(n)
    for n in names: visit(n)
    return out

T = ['"""Combat-related type definitions extracted from the Wizard101 reflection dump.',
     'Auto-generated by generate.py - do not edit by hand.',
     '',
     'Each dataclass mirrors a reflected class. Inherited fields come from the parent',
     'dataclass (the dump lists properties flattened; we de-duplicate them).',
     'Class attrs: _reflected = original reflected name, _hash = class hash, _bases = reflected bases.',
     'Enum-typed fields hold the matching IntEnum from enums.py (or None when the reflected default',
     'could not be mapped to a member). Lists model Vector/List containers; pointers are Optional."""',
     'from __future__ import annotations',
     'from dataclasses import dataclass, field',
     'from typing import Any, Optional', 'from .enums import *', '']
stubnames = sorted(s for s in stubs if s not in C or s not in inc)
T += ['# Referenced but intentionally not expanded (outside combat scope): opaque placeholders.']
for s in stubnames:
    T += ['@dataclass', f'class {pyname(s)}:', '    """stub - not expanded"""', '    pass', '']
for n in order(set(classes)):
    v = C[n]; par, props = own_props(n)
    pn = pyname(n)
    T += ['@dataclass', f'class {pn}({pyname(par)}):' if par else f'class {pn}:']
    T += [f'    _reflected = {v["name"]!r}', f'    _hash = {v["hash"]}', f'    _bases = {tuple(v["bases"])!r}']
    for k, p in props.items():
        fn = ident(k.replace('.', '_'))
        bt, dflt = base_py(p['type'], n)
        is_enum = p['type'].startswith('enum ')
        cont = p['container'] != 'Static'
        if is_enum:
            en = p['type'][5:]
            val = p.get('default') if p.get('default_status') == 'captured' else None
            member = None
            if en in ENUM and isinstance(val, int) and not isinstance(val, bool):
                member = next((ident(kk) for kk, x in ENUM[en].items() if x == val), None)
            dflt = f'{pyname(en)}.{member}' if member else 'None'
            ann = f'Optional[{bt}]' if not member else bt
        elif dflt is None:   # class ref
            dflt = 'None'; ann = f'Optional[{bt}]'
        else:
            ann = bt
            if p.get('default_status') == 'captured' and 'default' in p and not cont:
                d = p['default']
                dflt = repr(d) if isinstance(d, (int, float, str, bool)) else dflt
        if cont:
            ann = f'list[{ann}]'
            T.append(f'    {fn}: {ann} = field(default_factory=list)')
        else:
            T.append(f'    {fn}: {ann} = {dflt}')
    T.append('')
T += ['CLASSES = {']
T += [f'    {C[n]["name"]!r}: {pyname(n)},' for n in classes]
T += ['}', '']
def _desc(root):
    out, st = set(), [root]
    while st:
        x = st.pop()
        for y in subs.get(x, []):
            if y in set(classes) and y not in out: out.add(y); st.append(y)
    return out
tmpl = {r for r in ('CoreTemplate','BehaviorTemplate','GameEffectTemplate','GameEffectInfo') for r in _desc(r)|({r} if r in classes else set())}
T += ['# class hash -> class (for dispatching while parsing serialized data)', 'BY_HASH = {']
T += [f'    {C[n]["hash"]}: {pyname(n)},' for n in classes]
T += ['}', '', '# classes that are loaded as templates (CoreTemplate / BehaviorTemplate / GameEffectTemplate / GameEffectInfo trees)', 'TEMPLATE_CLASSES = {']
T += [f'    {C[n]["name"]!r}: {pyname(n)},' for n in sorted(tmpl)]
T += ['}', '']
open(f'{OUT}/types.py', 'w').write('\n'.join(T))
open(f'{OUT}/__init__.py', 'w').write('from .enums import *\nfrom .types import *\n')

# ---------------------------------------------------------------- JSON subset
sub = {'classes': {}, 'enums': {n: ENUM[n] for n in sorted(used_enums) if n in ENUM}}
for n in classes:
    v = C[n]
    sub['classes'][n] = {'name': v['name'], 'hash': v['hash'], 'bases': v['bases'],
        'properties': {k: {x: p[x] for x in ('type','id','offset','flags','container','pointer','hash','default') if x in p} for k, p in v['properties'].items()}}
json.dump(sub, open(f'{OUT}/combat_subset.json', 'w'), indent=1)

print(f'classes={len(classes)} enums={len(ENUM_PY)} stubs={len(stubnames)} enum_conflicts={conflicts} missing_enum_defs={missing_enum}')
print('stubs:', stubnames)
