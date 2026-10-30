import unittest
from fractions import Fraction
from queue_screen import Book, NS, CUTOFF, load_development, simulate, summarize, fraction_record

def book(seconds, ask=10100,bid=10000,aq=1,bq=4,valid=True):
    return Book(int(Fraction(str(seconds))*NS),ask,aq,bid,bq,valid)

class GuardedRows:
    def __init__(self,rows): self.rows=iter(rows); self.read=0
    def __iter__(self): return self
    def __next__(self):
        value=next(self.rows); self.read+=1; return value

class Controls(unittest.TestCase):
    def test_economic_boundary_does_not_consume_book_or_other_message_fields(self):
        messages=[['34500','1','1','1','10000','1'],['48600','DO NOT PARSE']]
        books=GuardedRows([['10100','1','10000','4'],['SECRET']])
        groups,record=load_development(messages,books)
        self.assertEqual(books.read,1)
        self.assertEqual(len(groups),1)
        self.assertFalse(record['boundary_book_read'])

    def test_final_tied_row_and_halt_resume(self):
        messages=[['34500','1','1','1','10000','1'],['34500','1','2','1','10000','1'],
                  ['34501','7','0','0','-1','-1'],['34502','7','0','0','0','-1'],
                  ['34503','7','0','0','1','-1'],['34504','1','3','1','10000','1'],['48600']]
        books=[['10100','1','10000','4'],['10200','2','10100','8']]+[['10200','2','10100','8']]*4
        groups,_=load_development(messages,books)
        self.assertEqual(groups[0].ask,10200)
        self.assertEqual(groups[0].bid_size,8)
        self.assertEqual([g.eligible for g in groups],[True,False,False,False,True])

    def test_signal_strictly_before_decision(self):
        groups=[book(34499.9,bq=1),book(34500,bq=100),book(34500.25),book(34501.5)]
        trades,counts=simulate(groups,[34500*NS],250,0,0,True)
        self.assertEqual(trades,[])
        self.assertEqual(counts['no_signal'],1)

    def test_tied_invalid_row_cannot_be_hidden_by_valid_final_row(self):
        messages=[['34500','6','1','1','10000','1'],
                  ['34500','1','2','1','10000','1'],['48600']]
        groups,_=load_development(messages,[['10100','1','10000','4']]*2)
        self.assertFalse(groups[0].eligible)
        self.assertEqual(groups[0].bid_size,4)

    def test_invalid_first_arrival_cancels_without_favorable_search(self):
        groups=[book(34499.9),book(34500.25,valid=False),
                book(34500.3),book(34501.55)]
        trades,counts=simulate(groups,[34500*NS],250,0,0,True)
        self.assertEqual(trades,[])
        self.assertEqual(counts['entry_canceled'],1)

    def test_delayed_touch_costs_and_no_midprice_fill(self):
        groups=[book(34499.9),book(34500.25,ask=10500),book(34501.5,bid=10400,ask=10600)]
        trades,_=simulate(groups,[34500*NS],250,30,100,True)
        self.assertEqual(len(trades),1)
        self.assertEqual(trades[0]['gross_units'],-100)
        self.assertEqual(trades[0]['net_units'],-360)
        self.assertGreater(trades[0]['entry_ns'],34500*NS)
        self.assertEqual(trades[0]['exit_ns'],34501.5*NS)

    def test_future_prices_cannot_create_signal(self):
        groups=[book(34499.9,bq=1),book(34500.25,bid=999999,ask=1000000),book(34501.5,bid=2000000,ask=2000001)]
        self.assertEqual(simulate(groups,[34500*NS],250,0,0,True)[0],[])

    def test_stale_signal_and_entry_deadline(self):
        groups=[book(34498),book(34500.9),book(34502.2)]
        self.assertEqual(simulate(groups,[34500*NS],250,0,0,True)[1]['stale_signal'],1)
        groups[0]=book(34499.9)
        self.assertEqual(simulate(groups,[34500*NS],250,0,0,True)[1]['entry_canceled'],1)

    def test_exit_failure_aborts_instead_of_dropping_trade(self):
        with self.assertRaisesRegex(ValueError,'open reference position'):
            simulate([book(34499.9),book(34500.25)],[34500*NS],250,0,0,True)

    def test_invalid_exit_waits_and_keeps_late_loss(self):
        groups=[book(34499.9),book(34500.25),book(34501.5,valid=False),book(34504,bid=9000)]
        trades,_=simulate(groups,[34500*NS],250,0,0,True)
        self.assertTrue(trades[0]['late_exit'])
        self.assertEqual(trades[0]['gross_units'],-1100)

    def test_no_overlapping_positions(self):
        groups=[book(34499.9),book(34500.25),book(34501.5),book(34503)]
        trades,counts=simulate(groups,[34500*NS,34501*NS],250,0,0,True)
        self.assertEqual(len(trades),1)
        self.assertEqual(counts['overlap'],1)

    def test_clock_reversal_and_pair_shape_stop(self):
        m=[['34500','1','1','1','10000','1'],['34499','1','1','1','10000','1'],['48600']]
        with self.assertRaises(ValueError): load_development(m,[['10100','1','10000','4']]*2)
        with self.assertRaises(ValueError): load_development(m[:1]+[['48600']],[['bad']])

    def test_malformed_values_abort_but_legitimate_empty_quotes_do_not(self):
        ordinary=['34500','1','1','1','10000','1']
        cases=[(ordinary[:4]+['-1','1'],['10100','1','10000','4']),
               (ordinary,['10100','-1','10000','4']),
               (ordinary,['9999999999','1','10000','4']),
               (ordinary,['10100','1','0','4']),
               (ordinary,['10100','1','10000','+4'])]
        for message,book_row in cases:
            with self.subTest(message=message,book=book_row), self.assertRaises(ValueError):
                load_development([message,['48600']],[book_row])
        for book_row in (['9999999999','0','10000','4'],['10000','1','10000','4'],
                         ['9900','1','10000','4']):
            groups,_=load_development([ordinary,['48600']],[book_row])
            self.assertFalse(groups[0].eligible)

    def test_changed_halt_book_aborts(self):
        messages=[['34500','1','1','1','10000','1'],['34501','7','0','0','-1','-1'],['48600']]
        with self.assertRaisesRegex(ValueError,'halt book changed'):
            load_development(messages,[['10100','1','10000','4'],['10200','1','10000','4']])

    def test_block_and_exposure_exact_arithmetic(self):
        trades,_=simulate([book(34499.9),book(34500.25),book(34501.5)],[34500*NS],250,30,100,True)
        result=summarize(trades,{})
        self.assertEqual(result['blocks'][0]['trades'],1)
        self.assertEqual(result['net_units'],-360)
        self.assertEqual(result['exposure_unit_ns'],10100*1250000000)
        self.assertEqual(fraction_record(Fraction(3,2)),{'numerator':3,'denominator':2})

if __name__ == "__main__": unittest.main()
