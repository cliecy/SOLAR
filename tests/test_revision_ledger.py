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

    def test_command_abstract_nested_braces(self):
        text, _ = ledger.source_section(r'\abstract{\textbf{Results:} 0.811} \section{Other} 0.2', 'Abstract')
        self.assertIn('0.811', text)
        self.assertNotIn('0.2', text)

    def test_percentage_and_sentence_final_short_decimal(self):
        rows = [dict(doc='main', location='4.6 Unknown-type rejection', printed='0.909'),
                dict(doc='main', location='4.6 Unknown-type rejection', printed='0.860')]
        receipt = ledger.extract_prose(rows, {'main': r'\section{Unknown} Recall 90.9\%; smoothness 0.86.'})
        self.assertEqual([r['printed'] for r in receipt], ['0.909', '0.86'])

    def test_stable_label_disambiguates_repeated_titles(self):
        tex = r'\section{Anchor geometry} 675 \label{sec:si-anchor-design} \section{Anchor geometry} 0.81 \label{sec:si-anchor-results}'
        section, _ = ledger.source_section(tex, 'SI 2.3')
        self.assertIn('675', section)
        self.assertNotIn('0.81', section)

    def test_integer_scientific_mantissa(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        from verify_paper_numbers import fmt_any
        self.assertEqual(fmt_any(0.00020001, r'+2\times10^{-4}'), r'+2\times10^{-4}')
        self.assertNotEqual(fmt_any(0.0004, r'+2\times10^{-4}'), r'+2\times10^{-4}')

    def test_current_table_dimensions_and_standard_errors(self):
        tex = r'''\label{tab:reviewer-main}
\multicolumn{4}{l}{30-dimensional outputs} \\
Orthogonal repeated & 0.811 \pm 0.034 & 0.912 & 0.86 \\
\end{tabular*}'''
        normalized = '\n'.join(ledger.re.sub(r'\s*&\s*', ' & ', line.strip().replace('$', '')) for line in tex.splitlines())
        result = ledger.Ledger()
        ledger.table4(result, normalized)
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0]['printed'], '0.811')


if __name__ == '__main__':
    unittest.main()
