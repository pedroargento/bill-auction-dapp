import unittest
from auction import *

class BidsTest(unittest.TestCase):
    def setUp(self):
        self.auction = Auction("auction_a", 200, 100, 100, 0.5)
        self.b1 = Bid("auction_a", 95, 100, 0.6, Address("alice"))
        self.b2 = Bid("auction_a", 95, 100, 0.4, Address("bob"))
        self.b3 = Bid("auction_a", 1100, 110, 0.7, Address("charles"))
        self.b4 = Bid("auction_b", 95, 100, 0.71, Address("evan"))
        self.b5 = Bid("auction_a", 95, 90, 0.8, Address("felicia"))

        self.bid_list = [self.b1, self.b2, self.b3, self.b4, self.b5]

    def test_valid_bids(self):
        expected_filtered_bids = [self.b1, self.b5]
        filtered_bids = list(filter_bids([self.b1, self.b2,self.b3,self.b4,self.b5], self.auction.id, self.auction.end_time, self.auction.reserve_price))
        self.assertEqual(filtered_bids, expected_filtered_bids, 'wrong list of filtered bids')

    def test_auction_output(self):
        VOLUME_LIMIT = 250
        bid_output1 = BidOutput(self.b1.bidder, self.b1.volume, 0)
        bid_output2 = BidOutput(self.b2.bidder, self.b2.volume, 0)
        bid_output3 = BidOutput(self.b3.bidder, self.b3.volume, 60)
        bid_output4 = BidOutput(self.b4.bidder, self.b4.volume, 100)
        bid_output5 = BidOutput(self.b5.bidder, self.b5.volume, 90)
        expected_outputs = [bid_output5, bid_output4, bid_output3, bid_output1, bid_output2]
        bids_outputs = list(auction_output(self.bid_list, VOLUME_LIMIT).bid_outputs)
        self.assertEqual(bids_outputs, expected_outputs, 'wrong list of outputs bids')
        sum_of_fullfill = sum([output.amount_fullfiled for output in bids_outputs])
        self.assertEqual(sum_of_fullfill, VOLUME_LIMIT)

    def test_auction_price(self):
        VOLUME_LIMIT = 250
        auction_outputs =  auction_output(self.bid_list, VOLUME_LIMIT)
        price = auction_price(auction_outputs)
        self.assertEqual(price, 0.7)

    def test_generate_bid_vouchers_no_fullfiled(self):
        price = 0.7
        output = BidOutput(Address('alice'), 100, 0)
        expected = [Voucher(Address('token_contract'), FunctionCall.TRANSFER, Address('alice'), 100, False)]
        self.assertEqual(generate_bid_vouchers(output, price), expected)

    def test_generate_bid_vouchers_mint(self):
        price = 0.7
        output = BidOutput(Address('alice'), 100, 70)
        expected = [Voucher(Address('token_contract'), FunctionCall.TRANSFER, Address('alice'), 30, False), Voucher(Address('token_contract'), FunctionCall.TRANSFER, Address('alice'), 70, True), Voucher(Address('mine_contract'), FunctionCall.MINT, Address('alice'), 30, True)]
        self.assertEqual(generate_bid_vouchers(output, price), expected)

    def test_generate_bid_vouchers_burn(self):
        price = 1.1
        output = BidOutput(Address('alice'), 100, 80)
        expected = [Voucher(Address('token_contract'), FunctionCall.TRANSFER, Address('alice'), 20, False), Voucher(Address('token_contract'), FunctionCall.TRANSFER, Address('alice'), 73, True), Voucher(Address('token_contract'), FunctionCall.TRANSFER, Address('mine_address'), int(7), True)]
        self.assertEqual(generate_bid_vouchers(output, price), expected)
if __name__ == '__main__':
    unittest.main()
