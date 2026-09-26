import copy
import unittest

from assess_eia_pit import ROOT, DOSSIER, assess, canonical, sha, strict_load, linked_file


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.dossier = strict_load((ROOT / DOSSIER).read_bytes())
        self.auth = strict_load((ROOT / self.dossier['authorization_path']).read_bytes())

    def resign(self, obj, field):
        obj[field] = sha(canonical({k: v for k, v in obj.items() if k != field}))

    def test_verified_transport_does_not_imply_pit(self):
        result = assess(self.dossier, self.auth)
        self.assertFalse(result['research_ready'])
        self.assertEqual(len(result['missing_fields_in_verified_response_schema']), 4)
        self.assertEqual(result, assess(copy.deepcopy(self.dossier), copy.deepcopy(self.auth)))

    def test_corrupted_digest_rejected(self):
        self.dossier['retrieved_at'] = '2015-03-09T00:00:00Z'
        with self.assertRaisesRegex(ValueError, 'DIGEST_MISMATCH'):
            assess(self.dossier, self.auth)

    def test_rehashed_readiness_claim_rejected(self):
        self.dossier['research_use_permitted'] = True
        self.resign(self.dossier, 'dossier_digest')
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_ADMISSION_CLAIM'):
            assess(self.dossier, self.auth)

    def test_extra_timestamp_column_cannot_clear_gate(self):
        self.dossier['transport_proof']['requested_fields'].append('published_at')
        self.auth['requested_row_fields'].append('published_at')
        self.resign(self.dossier['transport_proof'], 'proof_digest')
        self.resign(self.dossier, 'dossier_digest')
        with self.assertRaisesRegex(ValueError, 'SUPPLEMENTAL_EVIDENCE_REVIEW_REQUIRED'):
            assess(self.dossier, self.auth)

    def test_changed_authorized_dates_rejected(self):
        self.auth['requested_end'] = '2015-03-14'
        with self.assertRaisesRegex(ValueError, 'AUTHORIZATION_MISMATCH'):
            assess(self.dossier, self.auth)

    def test_duplicate_keys_and_noninteger_numbers_rejected(self):
        for bad in ['{"a":1,"a":2}', '{"a":1.1}', '{"a":NaN}']:
            with self.assertRaises(ValueError):
                strict_load(bad)

    def test_links_cannot_read_quarantine_or_arbitrary_paths(self):
        for path in ['data/quarantine/m4_eia_direct_01/key.dpapi', '../outside.json']:
            self.dossier['authorization_path'] = path
            with self.assertRaisesRegex(ValueError, 'LINK_NOT_ALLOWLISTED'):
                linked_file(self.dossier, 'authorization')


if __name__ == '__main__':
    unittest.main()
