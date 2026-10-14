from pathlib import Path
import json, shutil, os
from datetime import datetime
p = Path.home() / '.codex/models_cache.json'
d = json.loads(p.read_text())
changed = []
for model in d.get('models', []):
    for tier in model.get('service_tiers', []):
        if tier.get('id') == 'ultrafast' and tier.get('description') != '8 倍速度，8 倍消耗':
            tier['description'] = '8 倍速度，8 倍消耗'
            changed.append(model.get('slug'))
if changed:
    shutil.copy2(p, p.with_name(p.name + '.backup-' + datetime.now().strftime('%Y%m%d-%H%M%S')))
    tmp = p.with_name('.models_cache.text-update.tmp')
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
    os.chmod(tmp, p.stat().st_mode & 0o777)
    tmp.replace(p)
print('Updated:', ', '.join(changed) if changed else 'already current')
