import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
def fail(msg):
    raise ValueError(msg)
def pairs(items):
    result = dict(items)
    if len(items) != len(result):
        fail('duplicate keys')
    return result
def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
def load(name):
    raw = (root / name).read_bytes()
    obj = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                     parse_float=lambda _: fail('float'), parse_constant=lambda _: fail('constant'))
    assert raw == canonical(obj) + b'\n'
    return obj
def digest(obj, key):
    assert hashlib.sha256(canonical({k: v for k, v in obj.items() if k != key})).hexdigest() == obj[key]
d = load('evidence/m4/eia_direct_dossier_01.json')
a = load('evidence/m4/eia_direct_authorization_01.json')
l = load('evidence/m4/eia_direct_run_01.json')
digest(d, 'dossier_digest')
digest(d['transport_proof'], 'proof_digest')
for role in ('authorization', 'goal', 'ledger'):
    assert hashlib.sha256((root / d[role + '_path']).read_bytes()).hexdigest() == d[role + '_file_sha256']
assert d['dossier_id'] == a['dossier_id']
assert d['predecessor_dossier_ids'] == [a['predecessor_dossier_id']]
assert d['predecessor_dossier_digests'] == [a['predecessor_dossier_digest']]
assert d['pit_semantics'] == 'UNPROVEN' and not d['research_use_permitted']
assert len(l['attempts']) == 4
assert sum(x['received_bytes'] for x in l['attempts']) == d['total_body_bytes'] <= a['max_total_response_bytes']
for actual, route in zip(l['attempts'], a['approved_routes'], strict=True):
    assert actual['host'] == route['host'] and actual['endpoint'] == route['path']
    assert actual['state'] == 'RETAINED' and actual['http_status'] == 200
    assert subprocess.run(['git', 'check-ignore', '-q', actual['encrypted_locator']], cwd=root).returncode == 0
assert d['transport_proof']['raw_sha256'] == l['attempts'][-1]['raw_sha256']
for name in ['provider_evidence_contract_v2.json', 'provider_evidence_authorization_v2.json',
             'provider_evidence_manifest_v1.json', 'provider_licence_artifacts_v2.json']:
    p = 'evidence/m4/' + name
    assert subprocess.check_output(['git', 'show', 'b90a63f:' + p], cwd=root) == (root / p).read_bytes()
print('PASS: strict/canonical artifacts, all digests, lineage, limits, ignored raw and immutable predecessors')
