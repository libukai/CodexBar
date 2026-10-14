from pathlib import Path
root = Path(__file__).resolve().parents[1]
vortex = root / '.build/checkouts/Vortex'
assets = vortex / 'Sources/Vortex/Resources/Assets.xcassets'
raw = assets.with_name('Assets.precompiled')
if assets.exists() and not raw.exists():
    assets.rename(raw)
manifest = vortex / 'Package.swift'
s = manifest.read_text().replace('.process("Resources/Assets.xcassets")', '.copy("Resources/Assets.precompiled")').replace('.copy("Resources/Assets.xcassets")', '.copy("Resources/Assets.precompiled")')
manifest.chmod(0o644)
manifest.write_text(s)
kit = root / '.build/checkouts/KeyboardShortcuts/Sources/KeyboardShortcuts'
p = kit / 'ConflictPolicy.swift'
s = p.read_text()
old = '\t@Entry\n\tvar keyboardShortcutsConflictPolicy = KeyboardShortcuts.ConflictPolicy.default'
if old in s:
    s = s.replace(old, '''\tvar keyboardShortcutsConflictPolicy: KeyboardShortcuts.ConflictPolicy {
        get { self[KeyboardShortcutsConflictPolicyKey.self] }
        set { self[KeyboardShortcutsConflictPolicyKey.self] = newValue }
    }''')
    s += '''\nprivate struct KeyboardShortcutsConflictPolicyKey: EnvironmentKey {
    static var defaultValue: KeyboardShortcuts.ConflictPolicy { .default }
}\n'''
    p.chmod(0o644)
    p.write_text(s)
p = kit / 'Recorder.swift'
s = p.read_text()
if '#Preview {' in s and '#if CODEXBAR_ENABLE_PREVIEWS' not in s:
    start = s.index('#Preview {')
    s = s[:start] + '#if CODEXBAR_ENABLE_PREVIEWS\n' + s[start:]
    s = s.rsplit('#endif', 1)[0] + '#endif\n#endif\n'
    p.chmod(0o644)
    p.write_text(s)
print('Prepared dependencies for Command Line Tools + macOS 26.5 SDK')
