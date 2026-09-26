"""Offline diagnostic for the frozen EIA transport dossier, never a research gate."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOSSIER = 'evidence/m4/eia_direct_dossier_01.json'
REPORT = 'evidence/m4/eia_pit_readiness_01.json'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict_load(data):
    def pairs(items):
        result = dict(items)
        if len(result) != len(items):
            raise ValueError('DUPLICATE_KEY')
        return result

    def noninteger(_):
        raise ValueError('NONINTEGER_JSON')

    return json.loads(data, object_pairs_hook=pairs, parse_float=noninteger, parse_constant=noninteger)


def check_digest(value, field):
    material = {k: v for k, v in value.items() if k != field}
    if sha(canonical(material)) != value.get(field):
        raise ValueError('DIGEST_MISMATCH')


def assess(dossier, authorization):
    check_digest(dossier, 'dossier_digest')
    proof = dossier['transport_proof']
    check_digest(proof, 'proof_digest')
    if dossier['schema_id'] != 'M4_EIA_ENCRYPTED_DOSSIER_01':
        raise ValueError('UNSUPPORTED_SCHEMA')
    if (dossier['state'] != 'TRANSPORT_VERIFIED_EVIDENCE_ONLY'
            or dossier['pit_semantics'] != 'UNPROVEN'
            or dossier['research_use_permitted'] is not False
            or dossier['provider_selected_for_production'] is not False
            or authorization['values_may_enter_research'] is not False):
        raise ValueError('UNSUPPORTED_ADMISSION_CLAIM')
    if (dossier['dossier_id'] != authorization['dossier_id']
            or proof['requested_fields'] != authorization['requested_row_fields']
            or proof['requested_start'] != authorization['requested_start']
            or proof['requested_end'] != authorization['requested_end']):
        raise ValueError('AUTHORIZATION_MISMATCH')
    required = {
        'published_at': 'REAL_PUBLISHED_AT_MISSING',
        'available_at': 'REAL_AVAILABLE_AT_MISSING',
        'revision_id': 'REAL_SOURCE_VERSION_MISSING',
        'vintage_id': 'REAL_SOURCE_VERSION_MISSING',
    }
    fields = set(proof['requested_fields'])
    missing = sorted(set(required) - fields)
    # This diagnostic supports only the frozen transport schema; no string flag
    # or newly added column can stand in for a verified historical artifact.
    if len(missing) != len(required):
        raise ValueError('SUPPLEMENTAL_EVIDENCE_REVIEW_REQUIRED')
    result = {
        'schema_id': 'M4_EIA_PIT_READINESS_01',
        'assessment_scope': 'FROZEN_TRANSPORT_DOSSIER_ONLY',
        'source_dossier_id': dossier['dossier_id'],
        'source_dossier_digest': dossier['dossier_digest'],
        'transport_state': dossier['state'],
        'research_ready': False,
        'state': 'PIT_EVIDENCE_MISSING',
        'missing_fields_in_verified_response_schema': missing,
        'reason_codes': sorted({required[k] for k in missing}),
        'required_supplement': {
            'publication': 'First-party release evidence bound to each historical observation/version.',
            'availability': 'Verified availability with timezone, checked against the pre-frozen signal cutoff.',
            'version': 'Retained historical revision/vintage and selection rule; current retrieval is insufficient.',
        },
        'retrieval_timestamp_is_pit_evidence': False,
        'fixed_lag_is_pit_evidence': False,
        'provider_has_no_archive_asserted': False,
        'observations_read': False,
        'additional_api_requests': 0,
    }
    result['assessment_digest'] = sha(canonical(result))
    return result


def linked_file(dossier, role):
    allowed = {
        'authorization': 'evidence/m4/eia_direct_authorization_01.json',
        'goal': 'agent/goals/2026-09-25_m4_eia_encrypted_probe.md',
        'ledger': 'evidence/m4/eia_direct_run_01.json',
    }
    if role not in allowed or dossier[role + '_path'] != allowed[role]:
        raise ValueError('LINK_NOT_ALLOWLISTED')
    path = (ROOT / dossier[role + '_path']).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('LINK_OUTSIDE_REPOSITORY')
    data = path.read_bytes()
    if sha(data) != dossier[role + '_file_sha256']:
        raise ValueError('LINK_DIGEST_MISMATCH')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    dossier = strict_load((ROOT / DOSSIER).read_bytes())
    authorization = strict_load(linked_file(dossier, 'authorization'))
    linked_file(dossier, 'goal')
    strict_load(linked_file(dossier, 'ledger'))
    report = canonical(assess(dossier, authorization)) + b'\n'
    if args.check:
        if report != (ROOT / REPORT).read_bytes():
            raise ValueError('ASSESSMENT_NOT_REPRODUCIBLE')
        print('PASS: deterministic assessment; transport evidence retained; historical research gate closed')
    else:
        print(report.decode(), end='')


if __name__ == '__main__':
    main()
