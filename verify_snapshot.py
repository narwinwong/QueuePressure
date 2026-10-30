"""Offline public snapshot and saved arithmetic checks, no engine import."""
from fractions import Fraction
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ALLOWED={'.gitattributes','.gitignore','AUDIT.md','PROTOCOL.md','README.md','REPORT.md','SNAPSHOT_MANIFEST.json','results.json','queue_screen.py','test_queue_screen.py','plot_results.py','verify_snapshot.py','requirements.txt','figures/conditional_margins.png'}
def verify():
    actual={str(p.relative_to(ROOT)).replace('\\','/') for p in ROOT.rglob('*') if p.is_file() and not any(part in ('.git','__pycache__','regenerated') for part in p.relative_to(ROOT).parts)}
    if actual!=ALLOWED: raise ValueError('snapshot allowlist mismatch')
    manifest=json.loads((ROOT/'SNAPSHOT_MANIFEST.json').read_text(encoding='utf-8'))
    if set(manifest['files'])!=ALLOWED-{'SNAPSHOT_MANIFEST.json'}: raise ValueError('manifest set mismatch')
    for name,digest in manifest['files'].items():
        blob=(ROOT/name).read_bytes()
        if not name.endswith('.png'): blob=blob.replace(b'\r\n',b'\n')
        if hashlib.sha256(blob).hexdigest()!=digest: raise ValueError('snapshot changed: '+name)
    s=json.loads((ROOT/'results.json').read_text(encoding='utf-8'))
    if s['disposition']!='FIXED_REFERENCE_SCREEN_FAIL' or any(s[k] is not False for k in ('verified_edge','confirmation_authorized','empirical_oos')): raise ValueError('unsupported claim')
    fees={'zero_cost':0,'primary':260,'fee_double':320,'slip_double':460,'delay_stress':260}
    if set(s['scenarios'])!=set(fees): raise ValueError('scenario set')
    for name,cost in fees.items():
        row=s['scenarios'][name]
        for policy in ('pressure','unfiltered'):
            p=row[policy]
            if p['net_units']!=p['gross_units']-p['trades']*cost: raise ValueError('cost identity')
            if p['trades']+sum(p['counts'].values())!=1409: raise ValueError('decision accounting')
            if sum(b['trades'] for b in p['blocks'])!=p['trades'] or sum(b['net_units'] for b in p['blocks'])!=p['net_units']: raise ValueError('block accounting')
            if p['units_per_usd']!=10000 or not 0<=p['late_exits']<=p['trades']: raise ValueError('unit/count')
        a,b=row['pressure'],row['unfiltered']
        expected=Fraction(a['net_units'])-Fraction(a['exposure_unit_ns'],b['exposure_unit_ns'])*b['net_units']
        v=row['exposure_matched_excess_units']
        if expected!=Fraction(v['numerator'],v['denominator']) or row['cash_reference_units']!=0: raise ValueError('control identity')
    p=s['scenarios']['primary']['pressure']
    if p['trades']!=117 or p['net_units']!=-236520 or p['late_exits']!=40 or any(b['net_units']>=0 for b in p['blocks']): raise ValueError('reported primary result')
    print('PASS: reviewed public snapshot and saved aggregate arithmetic; no raw replay')
if __name__=='__main__': verify()
