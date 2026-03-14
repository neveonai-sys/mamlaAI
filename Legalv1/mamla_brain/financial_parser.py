def detect_financial_rows(text):
    rows = []
    for line in (text or '').splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if any(token in candidate.lower() for token in ('emi', 'installment', 'principal', 'interest', 'balance')):
            rows.append(candidate)
    return rows


def render_financial_context(text):
    rows = detect_financial_rows(text)
    if not rows:
        return ''
    return '--- FINANCIAL DATA ---\n' + '\n'.join(rows)
