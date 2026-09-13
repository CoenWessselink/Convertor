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


REQUIRED_PROFILE_FAMILIES = (
    'HEA', 'HEB', 'HEM', 'IPE', 'IPN', 'UNP', 'UPN', 'UPE',
    'L', 'T', 'RHS', 'SHS', 'CHS', 'ROUND', 'SQUARE', 'FLAT', 'STRIP',
)


def profile_catalog_coverage(rows, *, required_families=REQUIRED_PROFILE_FAMILIES):
    """Return explicit catalog coverage without turning aliases into products.

    The result is deliberately conservative. A geometrically compatible FLAT
    entry does not prove a STRIP product origin, and UPN does not prove UNP/UPE.
    Missing families are a data gap rather than a recognition PASS.
    """
    available = set()
    counts = {}
    for row in rows or ():
        if not isinstance(row, dict):
            continue
        family = str(row.get('family') or '').strip().upper()
        profile_type = str(row.get('profile_type') or '').strip().upper()
        designation = str(row.get('designation') or '').strip().upper()
        tokens = {family}
        if profile_type == 'L': tokens.add('L')
        if profile_type == 'RU' or family == 'ROUND': tokens.add('ROUND')
        if profile_type == 'Q' or family == 'SQUARE': tokens.add('SQUARE')
        if profile_type == 'B' and family == 'FLAT': tokens.add('FLAT')
        for prefix in ('HEA','HEB','HEM','IPE','IPN','UNP','UPN','UPE','RHS','SHS','CHS','STRIP'):
            if designation.startswith(prefix) or family == prefix:
                tokens.add(prefix)
        if profile_type == 'T' or family == 'T' or designation.startswith('T'):
            tokens.add('T')
        for token in tokens - {''}:
            available.add(token)
            counts[token] = counts.get(token, 0) + 1
    required = tuple(str(item).upper() for item in required_families)
    missing = tuple(item for item in required if item not in available)
    return {
        'passed': not missing,
        'status': 'PASS' if not missing else 'PARTIAL',
        'required': list(required),
        'covered': [item for item in required if item in available],
        'missing': list(missing),
        'counts': {item: counts.get(item, 0) for item in required},
        'blocking_codes': ['BLOCKED_DATA:PROFILE_CATALOG:' + item for item in missing],
        'scope': 'catalog entries only; no inferred product origin from geometric aliases',
    }
