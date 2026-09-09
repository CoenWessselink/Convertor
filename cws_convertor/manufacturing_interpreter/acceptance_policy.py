"""Explicit useful-recognition AND false-ready acceptance, never one alone."""
from __future__ import annotations
from math import isfinite


def corpus_verdict(summary, *, required_positive_ids=('01', '02'), min_precision=0.95, min_recall=0.90, rows=()):
    """Engineering defaults are versioned here, not fitted to observed results.

    This is a synthetic regression threshold, not external accuracy certification.
    Independent supplier/model corpora remain separate evidence.
    """
    codes = []
    for key, minimum in (('precision', min_precision), ('recall', min_recall)):
        value = summary.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not minimum <= value <= 1:
            codes.append(key.upper() + '_BELOW_THRESHOLD_OR_MISSING')
    if summary.get('true_positive', 0) <= 0:
        codes.append('NO_CORRECT_POSITIVE_RECOGNITION')
    if summary.get('false_ready') != 0:
        codes.append('FALSE_READY_OR_MISSING_SAFETY_PROOF')
    if summary.get('errors') or summary.get('deterministic_repeat_failures') != 0:
        codes.append('ERROR_OR_NONDETERMINISM')
    by_id = {str(r.get('id')): r for r in rows}
    for identifier in required_positive_ids:
        row = by_id.get(identifier, {})
        if row.get('readiness') != 'READY' or row.get('unsafe_ready') is not False:
            codes.append('POSITIVE_REFERENCE_NOT_READY:' + identifier)
    return {'passed': not codes, 'blocking_codes': codes, 'policy': 'mgi-usefulness-1',
            'minimum_precision': min_precision, 'minimum_recall': min_recall,
            'required_positive_ids': list(required_positive_ids), 'scope': 'synthetic corpus, not supplier certification'}
