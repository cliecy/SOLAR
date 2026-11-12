"""Regression cases for silent loss or misplaced manuscript claims.

Small invented TeX snippets exercise parser behavior; no manuscript is bundled.
"""
import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('ledger', Path(__file__).resolve().parents[1] / 'scripts/build_revision_ledger.py')
assert spec is not None and spec.loader is not None
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)


class LedgerRegressionTests(unittest.TestCase):
    def test_wrong_section_cannot_supply_number(self):
        tex = r'\section{Matched controls} 0.812 \section{Other} 0.811'
        rows = [dict(doc='main', location='4.3 Matched controls', printed='0.811')]
        with self.assertRaisesRegex(ValueError, 'missing numeric token'):
            ledger.extract_prose(rows, {'main': tex})

    def test_numeric_substring_is_not_a_match(self):
        rows = [dict(doc='main', location='4.3 Matched controls', printed='0.81')]
        with self.assertRaises(ValueError):
            ledger.extract_prose(rows, {'main': r'\section{Matched controls} 0.811'})

    def test_exact_section_token_is_extracted(self):
        rows = [dict(doc='main', location='4.3 Matched controls', printed='0.811')]
        result = ledger.extract_prose(rows, {'main': '\\section{Matched controls}\n score $0.811$\n\\section{Other} 0.7'})
        self.assertEqual(result[0]['printed'], '0.811')
        self.assertIn('score', result[0]['context'])

    def test_missing_rows_fail_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            reference = Path(tmp) / 'reference.csv'
            reference.write_text('doc,location\nmain,Table 4\nmain,Table 4\n')
            with self.assertRaisesRegex(ValueError, 'claim population changed'):
                ledger.check_expected_counts([dict(doc='main', location='Table 4')], reference)

    def test_math_delimited_dimensions(self):
        tex = r'''\label{tab:reviewer-main}
Orthogonal repeated & $30$ & 0.811 \\
\end{tabular*}'''
        normalized = '\n'.join(ledger.re.sub(r'\s*&\s*', ' & ', line.strip().replace('$', '')) for line in tex.splitlines())
        result = ledger.Ledger()
        ledger.table4(result, normalized)
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0]['printed'], '0.811')


if __name__ == '__main__':
    unittest.main()
