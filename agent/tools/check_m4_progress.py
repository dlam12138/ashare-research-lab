"""One-command offline M4 progress check for the frozen EIA transport dossier.

Read-only diagnostic with fixed repository-relative metadata paths: no argument
selects a root, path, source, provider or database. No network, no writes, no
current-time or environment reads, no raw observation values, no credentials and
no transport proof material in the output.

Exit 0: diagnostic completed. The evidence checks passed and historical research
is still blocked by missing first-party PIT evidence.
Exit 2: evidence validation failed (fail closed, sanitized error code only).
"""
import argparse
import json
import sys
from pathlib import Path

from assess_eia_pit import DOSSIER, REPORT, assess, canonical, sha, strict_load
from assess_eia_pit import ROOT as REPOSITORY_ROOT

SCHEMA_ID = 'M4_OFFLINE_PROGRESS_CHECK_01'
ASSESSMENT_SCOPE = 'FROZEN_EIA_TRANSPORT_DOSSIER_ONLY'
AUTHORIZATION_SCHEMA_ID = 'M4_EIA_DIRECT_AUTHORIZATION_01'
LEDGER_SCHEMA_ID = 'M4_EIA_ENCRYPTED_RUN_01'
SCOPE_NOTE = (
    'Not a complete K2 or whole-project readiness assessment: this check covers only the '
    'frozen EIA transport dossier metadata and its retained PIT assessment.'
)
NEXT_TASK = (
    'Separately scoped first-party historical PIT evidence review (publication, availability, '
    'revision/vintage) before any new acquisition, provider selection or execution.'
)
LINKED_ALLOWLIST = {
    'authorization': 'evidence/m4/eia_direct_authorization_01.json',
    'goal': 'agent/goals/2026-09-25_m4_eia_encrypted_probe.md',
    'ledger': 'evidence/m4/eia_direct_run_01.json',
}
# Only these fixed codes may reach stdout/stderr; everything else is collapsed so
# that no artifact value, path or traceback can leak through an error message.
SAFE_ERROR_CODES = frozenset({
    'ASSESSMENT_NOT_REPRODUCIBLE',
    'AUTHORIZATION_MISMATCH',
    'DIGEST_MISMATCH',
    'DUPLICATE_KEY',
    'EVIDENCE_FILE_MISSING',
    'EVIDENCE_JSON_INVALID',
    'EVIDENCE_PATH_OUTSIDE_ROOT',
    'EVIDENCE_READ_FAILED',
    'EVIDENCE_SCHEMA_INVALID',
    'EVIDENCE_VALIDATION_FAILED',
    'FROZEN_IDENTITY_MISMATCH',
    'LINK_DIGEST_MISMATCH',
    'LINK_NOT_ALLOWLISTED',
    'LINK_OUTSIDE_REPOSITORY',
    'NONINTEGER_JSON',
    'SUPPLEMENTAL_EVIDENCE_REVIEW_REQUIRED',
    'UNSUPPORTED_ADMISSION_CLAIM',
    'UNSUPPORTED_SCHEMA',
})


class EvidenceError(Exception):
    """Sanitized evidence-validation failure; never carries artifact content."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _read_fixed(root, relative, outside_code):
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise EvidenceError(outside_code)
    try:
        return resolved.read_bytes()
    except FileNotFoundError:
        raise EvidenceError('EVIDENCE_FILE_MISSING') from None
    except OSError:
        raise EvidenceError('EVIDENCE_READ_FAILED') from None


def _linked_bytes(root, dossier, role):
    if not isinstance(dossier, dict):
        raise EvidenceError('EVIDENCE_SCHEMA_INVALID')
    if dossier.get(role + '_path') != LINKED_ALLOWLIST[role]:
        raise EvidenceError('LINK_NOT_ALLOWLISTED')
    data = _read_fixed(root, LINKED_ALLOWLIST[role], 'LINK_OUTSIDE_REPOSITORY')
    if sha(data) != dossier.get(role + '_file_sha256'):
        raise EvidenceError('LINK_DIGEST_MISMATCH')
    return data


def _sanitized_code(exc):
    if isinstance(exc, EvidenceError):
        return exc.code
    if isinstance(exc, json.JSONDecodeError):
        return 'EVIDENCE_JSON_INVALID'
    if isinstance(exc, FileNotFoundError):
        return 'EVIDENCE_FILE_MISSING'
    if isinstance(exc, KeyError):
        return 'EVIDENCE_SCHEMA_INVALID'
    if isinstance(exc, ValueError):
        message = str(exc).strip()
        if message in SAFE_ERROR_CODES:
            return message
    return 'EVIDENCE_VALIDATION_FAILED'


def _build(root):
    dossier = strict_load(_read_fixed(root, DOSSIER, 'EVIDENCE_PATH_OUTSIDE_ROOT'))
    authorization = strict_load(_linked_bytes(root, dossier, 'authorization'))
    _linked_bytes(root, dossier, 'goal')
    ledger = strict_load(_linked_bytes(root, dossier, 'ledger'))
    if not isinstance(dossier, dict) or not isinstance(authorization, dict):
        raise EvidenceError('EVIDENCE_SCHEMA_INVALID')
    if authorization.get('schema_id') != AUTHORIZATION_SCHEMA_ID:
        raise EvidenceError('UNSUPPORTED_SCHEMA')
    if ledger.get('schema_id') != LEDGER_SCHEMA_ID:
        raise EvidenceError('FROZEN_IDENTITY_MISMATCH')
    if (
        dossier.get('predecessor_dossier_ids') != [authorization.get('predecessor_dossier_id')]
        or dossier.get('predecessor_dossier_digests')
        != [authorization.get('predecessor_dossier_digest')]
        or dossier.get('pit_semantics') != authorization.get('pit_status')
        or dossier.get('goal_path') != authorization.get('goal_path')
    ):
        raise EvidenceError('FROZEN_IDENTITY_MISMATCH')
    # The retained readiness flag is never trusted: the assessment is recomputed
    # from the verified dossier and then compared byte for byte to the retained file.
    assessment = assess(dossier, authorization)
    retained = _read_fixed(root, REPORT, 'EVIDENCE_PATH_OUTSIDE_ROOT')
    if canonical(assessment) + b'\n' != retained:
        raise EvidenceError('ASSESSMENT_NOT_REPRODUCIBLE')
    return {
        'schema_id': SCHEMA_ID,
        'assessment_scope': ASSESSMENT_SCOPE,
        'scope_note': SCOPE_NOTE,
        'source_dossier_id': assessment['source_dossier_id'],
        'source_dossier_digest': assessment['source_dossier_digest'],
        'transport_state': assessment['transport_state'],
        'evidence_checks': {
            'dossier_digest': 'VERIFIED',
            'transport_proof_digest': 'VERIFIED',
            'linked_authorization': 'ALLOWLISTED_DIGEST_MATCH',
            'linked_goal': 'ALLOWLISTED_DIGEST_MATCH',
            'linked_ledger': 'ALLOWLISTED_DIGEST_MATCH',
            'frozen_identity': 'MATCH',
            'retained_assessment_reproduced': True,
            'passed': True,
        },
        'evidence_checks_passed': True,
        'research_blocked': True,
        'research_ready': False,
        'execution_authorized': False,
        'research_state': assessment['state'],
        'reason_codes': assessment['reason_codes'],
        'missing_fields_in_verified_response_schema': assessment[
            'missing_fields_in_verified_response_schema'
        ],
        'required_supplement': assessment['required_supplement'],
        'limits': {
            'not_a_complete_k2_or_whole_project_readiness_assessment': True,
            'eia_frozen_dossier_metadata_only': True,
            'provider_has_no_archive_asserted': assessment['provider_has_no_archive_asserted'],
            'monthly_to_daily_conversion_performed': False,
            'observations_read': assessment['observations_read'],
            'additional_api_requests': assessment['additional_api_requests'],
        },
        'retained_assessment_digest': assessment['assessment_digest'],
        'next_task': NEXT_TASK,
        'result': 'DIAGNOSTIC_COMPLETE_RESEARCH_BLOCKED',
    }


def build_progress_report(root):
    """Return the deterministic read-only report for ``root`` or raise EvidenceError."""
    try:
        return _build(Path(root))
    except EvidenceError:
        raise
    except Exception as exc:
        raise EvidenceError(_sanitized_code(exc)) from None


def _flag(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def render_text(report):
    lines = [
        'M4 OFFLINE PROGRESS CHECK (read-only, offline, metadata only)',
        f"schema_id: {report['schema_id']}",
        f"assessment_scope: {report['assessment_scope']}",
        f"scope_note: {report['scope_note']}",
        f"source_dossier_id: {report['source_dossier_id']}",
        f"source_dossier_digest: {report['source_dossier_digest']}",
        f"transport_state: {report['transport_state']}",
        '',
        "evidence_checks: PASSED",
    ]
    for key in sorted(report['evidence_checks']):
        lines.append(f"  {key}: {_flag(report['evidence_checks'][key])}")
    lines += [
        f"evidence_checks_passed: {_flag(report['evidence_checks_passed'])}",
        '',
        f"research_blocked: {_flag(report['research_blocked'])}",
        f"research_ready: {_flag(report['research_ready'])}",
        f"execution_authorized: {_flag(report['execution_authorized'])}",
        f"research_state: {report['research_state']}",
        f"reason_codes: {', '.join(report['reason_codes'])}",
        'missing_fields_in_verified_response_schema: '
        + ', '.join(report['missing_fields_in_verified_response_schema']),
        'required_supplement:',
    ]
    for key in sorted(report['required_supplement']):
        lines.append(f"  {key}: {report['required_supplement'][key]}")
    lines += ['', 'limits:']
    for key in sorted(report['limits']):
        lines.append(f"  {key}: {_flag(report['limits'][key])}")
    lines += [
        '',
        f"retained_assessment_digest: {report['retained_assessment_digest']}",
        f"next_task: {report['next_task']}",
        f"result: {report['result']}",
        'exit_code: 0',
    ]
    return '\n'.join(lines) + '\n'


def _emit(text):
    buffer = getattr(sys.stdout, 'buffer', None)
    if buffer is None:
        sys.stdout.write(text)
    else:
        buffer.write(text.encode('utf-8'))


def _emit_failure(code, as_json):
    if as_json:
        _emit(canonical({
            'schema_id': SCHEMA_ID,
            'result': 'EVIDENCE_VALIDATION_FAILED',
            'error_code': code,
            'exit_code': 2,
        }).decode('utf-8') + '\n')
    else:
        _emit(f'EVIDENCE_VALIDATION_FAILED: {code}\nexit_code: 2\n')


def main(argv=None, root=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='emit the report as canonical JSON')
    args = parser.parse_args(argv)
    try:
        report = build_progress_report(REPOSITORY_ROOT if root is None else root)
    except Exception as exc:  # fail closed: sanitized code only, never a traceback
        _emit_failure(_sanitized_code(exc), args.json)
        return 2
    _emit(canonical(report).decode('utf-8') + '\n' if args.json else render_text(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
