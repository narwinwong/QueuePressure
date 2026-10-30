"""Public pure engine extraction; no data acquisition or production driver."""
from bisect import bisect_left
from decimal import Decimal
from fractions import Fraction
import re
from typing import NamedTuple

NS = 10**9

CUTOFF = 48600*NS

SCENARIOS = {'zero_cost': (250,0,0), 'primary': (250,30,100),
             'fee_double': (250,60,100), 'slip_double': (250,30,200),
             'delay_stress': (1000,30,100)}

BLOCKS = (34500,37800,41400,45000,48600)

class Book(NamedTuple):
    time: int
    ask: int
    ask_size: int
    bid: int
    bid_size: int
    eligible: bool

def time_ns(value):
    number = Decimal(value)
    if not number.is_finite() or number*NS != (number*NS).to_integral_value():
        raise ValueError('finite nanosecond time required')
    return int(number*NS)

def integer(value):
    if re.fullmatch(r'-?\d+', value) is None:
        raise ValueError('integer field required')
    return int(value)

def load_development(message_rows, book_rows):
    books = iter(book_rows)
    groups, previous, halted, previous_book = [], None, False, None
    rows, boundary = 0, False
    for message in message_rows:
        # Only the boundary time is read. No boundary book or other fields consumed.
        t = time_ns(message[0])
        if t >= CUTOFF:
            boundary = True
            break
        rows += 1
        if rows > 500000 or len(message) != 6 or t < 34200*NS or (previous is not None and t < previous):
            raise ValueError('development shape/time/budget failure')
        previous = t
        row = next(books, None)
        if row is None or len(row) != 4:
            raise ValueError('paired development row unavailable')
        kind, identity, size, price, direction = map(integer, message[1:])
        if kind not in range(1,8) or identity < 0 or size < 0 or direction not in (-1,1):
            raise ValueError('development message invalid')
        if kind != 7 and price < 0:
            raise ValueError('negative event price')
        if kind == 7:
            if identity != 0 or size != 0 or direction != -1 or price not in (-1,0,1):
                raise ValueError('halt message invalid')
            halted = price != 1
        ask, aq, bid, bq = map(integer,row)
        if min(aq,bq) < 0 or (aq > 0 and ask <= 0) or (bq > 0 and bid <= 0):
            raise ValueError('book quantity/price invalid')
        if (abs(ask) == 9999999999 and aq != 0) or (abs(bid) == 9999999999 and bq != 0):
            raise ValueError('dummy level with nonzero size')
        if kind == 7 and previous_book is not None and tuple((ask,aq,bid,bq)) != previous_book:
            raise ValueError('halt book changed')
        previous_book = (ask,aq,bid,bq)
        valid = not halted and kind not in (6,7) and 0 < bid < ask < 9999999999 and aq >= 1 and bq >= 1
        group = Book(t,ask,aq,bid,bq,valid)
        if groups and groups[-1].time == t:
            group = group._replace(eligible=group.eligible and groups[-1].eligible)
            groups[-1] = group
        else:
            groups.append(group)
    if not boundary or not groups:
        raise ValueError('economic boundary not reached without seal access')
    return groups, {'development_rows': rows, 'completed_groups': len(groups),
                    'boundary_time_only_peek': True, 'boundary_book_read': False}

def simulate(groups, decisions, delay_ms, fee, adverse, filtered):
    clocks = [g.time for g in groups]
    trades, counts, previous_exit = [], {'stale_signal':0,'no_signal':0,'entry_canceled':0,'overlap':0}, -1
    delay = delay_ms*10**6
    for decision in decisions:
        if decision <= previous_exit:
            counts['overlap'] += 1
            continue
        i = bisect_left(clocks,decision)-1
        if i < 0 or not groups[i].eligible or decision-clocks[i] > NS:
            counts['stale_signal'] += 1
            continue
        signal = groups[i]
        if filtered and signal.bid_size < 4*signal.ask_size:
            counts['no_signal'] += 1
            continue
        arrival = decision+delay
        j = bisect_left(clocks,arrival)
        if j == len(groups) or clocks[j]-arrival > NS//2 or not groups[j].eligible:
            counts['entry_canceled'] += 1
            continue
        entry = groups[j]
        target = entry.time+NS+delay
        k = bisect_left(clocks,target)
        while k < len(groups) and not groups[k].eligible:
            k += 1
        if k == len(groups):
            raise ValueError('open reference position: no exit before seal; entire screen stops')
        exit_book = groups[k]
        holding = exit_book.time-entry.time
        gross = exit_book.bid-entry.ask
        trades.append({'decision_ns':decision,'signal_ns':signal.time,'entry_ns':entry.time,
                       'exit_ns':exit_book.time,'entry_ask_units':entry.ask,'exit_bid_units':exit_book.bid,
                       'signal_bid_size':signal.bid_size,'signal_ask_size':signal.ask_size,
                       'entry_ask_size':entry.ask_size,'exit_bid_size':exit_book.bid_size,
                       'gross_units':gross,'net_units':gross-2*fee-2*adverse,
                       'holding_ns':holding,'late_exit':holding>2*NS,
                       'exposure_unit_ns':entry.ask*holding})
        previous_exit = exit_book.time
    return trades, counts

def fraction_record(value):
    value = Fraction(value)
    return {'numerator':value.numerator,'denominator':value.denominator}

def summarize(trades, counts):
    blocks = []
    for start, end in zip(BLOCKS[:-1],BLOCKS[1:]):
        selected = [t for t in trades if start*NS <= t['decision_ns'] < end*NS]
        blocks.append({'start_seconds':start,'end_seconds':end,'trades':len(selected),
                       'net_units':sum(t['net_units'] for t in selected)})
    return {'trades':len(trades),'net_units':sum(t['net_units'] for t in trades),
            'gross_units':sum(t['gross_units'] for t in trades),'units_per_usd':10000,
            'late_exits':sum(t['late_exit'] for t in trades),
            'exposure_unit_ns':sum(t['exposure_unit_ns'] for t in trades),
            'blocks':blocks,'counts':counts}

def evaluate(groups):
    decisions = [t*NS for t in range(34500,48581,10)]
    result, ledger = {}, {}
    for name,(delay,fee,adverse) in SCENARIOS.items():
        policies = {}
        for policy,filtered in [('pressure',True),('unfiltered',False)]:
            trades,counts = simulate(groups,decisions,delay,fee,adverse,filtered)
            ledger[name+'_'+policy] = trades
            policies[policy] = summarize(trades,counts)
        a,b = policies['pressure'],policies['unfiltered']
        matched = None if not b['exposure_unit_ns'] else Fraction(a['net_units']) - Fraction(
            a['exposure_unit_ns'],b['exposure_unit_ns'])*b['net_units']
        policies['cash_reference_units'] = 0
        policies['exposure_matched_excess_units'] = None if matched is None else fraction_record(matched)
        result[name] = policies
    primary = result['primary']['pressure']
    excess = result['primary']['exposure_matched_excess_units']
    support = primary['trades'] >= 30 and all(b['trades'] >= 5 for b in primary['blocks'])
    passed = support and primary['net_units'] > 0 and excess is not None and excess['numerator'] > 0 and all(
        b['net_units'] > 0 for b in primary['blocks']) and primary['late_exits'] == 0
    return {'classification':'CONDITIONAL_TRADE_MARGIN_NOT_FUNDED_PNL',
            'disposition': ('POSITIVE_REFERENCE_ONLY_UNQUALIFIED' if passed else
                            'FIXED_REFERENCE_SCREEN_FAIL' if support else 'INSUFFICIENT_SUPPORT'),
            'scenarios':result,'financial_family':'E18','verified_edge':False,
            'confirmation_authorized':False,'empirical_oos':False}, ledger
