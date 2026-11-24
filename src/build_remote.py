"""marble_run_remote.html = the Spire remote's core (verbatim) + the marble run's palette and panels (remote/config.js)."""
src = open('/mnt/user-data/uploads/1e2885aa-spire_remote.html').read().split('\n')
out = src[0:5] + ['<title>Grand Marble Run - host remote</title>',
 '<link rel="preconnect" href="https://fonts.googleapis.com">',
 '<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700;900&family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">']
out += src[8:95]
out += ['/* Golden grand prix: night, polished black, gold */',
':root { --bg: #07080d; --panel: #11131c; --edge: #3a3220; --gold: #f2c45a; --ink: #f4f0e6; --muted: #b3aa94; --sky: #f7dc94; --safe: #7ef0a8; --danger: #ff5a5a;',
'  --well: #0a0b11; --btn: #23232e; --glow1: #3a2c10; --glow2: #0e0f16; --h2: #f2c45a; --lit: #8a6a14; --lit-glow: rgba(242,196,90,.5);',
'  --title: "Cinzel", Georgia, serif; --title-w: 700; --title-ls: .05em; --h2-size: 20px; --go: #1f6038; --stop: #7a2222; --warn: #7a5a14; --skyb: #4a3a14; }',
'h1 { font-size: 40px; color: #f7dc94; text-shadow: 0 0 22px rgba(242,196,90,.45); }',
'.chip.idle { background: #26262e; color: var(--muted); } .chip.over { background: #4a3a10; color: var(--gold); }',
'td.hero { color: var(--gold); font-weight: 700; }',
'.tm { background: transparent; }',
'details.cheat { background: var(--well); border-radius: 10px; padding: 8px 12px; }',
'details.cheat summary { cursor: pointer; font-weight: 700; color: var(--gold); }',
'details.cheat dl { margin: 8px 0 0; } details.cheat dt { color: var(--sky); font-weight: 700; margin-top: 8px; } details.cheat dd { margin: 2px 0 0 0; }',
'</style>', '</head>', '<body>']
core = src[112:480]
assert core[0] == '<script>' and core[-1] == '</script>'
out += core + open('/home/claude/mr/remote/config.js').read().split('\n')
open('/home/claude/mr/marble_run_remote.html', 'w').write('\n'.join(out))
print("remote", len('\n'.join(out)) // 1024, "KB")
