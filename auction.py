from collections.abc import Iterable
from itertools import accumulate, starmap, chain
from typing import NamedTuple
from enum import Enum

class Auction(NamedTuple):
    id: str
    end_time: int
    lock_time: int
    volume_limit: float
    reserve_price: float

class Bid(NamedTuple):
    auction_id: str
    timestamp: int
    volume: float
    price: float
    bidder: str

class BidOutput(NamedTuple):
    bidder: str
    amount_sent: float
    amount_fullfiled: float

class AuctionOutput(NamedTuple):
    bid_outputs: Iterable[BidOutput]
    sorted_bids: Iterable[Bid]

TokenOperation = Enum('TokenOperation', ['TRANSFER', 'MINT', 'BURN'])
class Voucher(NamedTuple):
    target: str
    operation: TokenOperation
    amount: float
    timestamp_locked: bool

def filter_bids(bids: Iterable[Bid], auction_id: str, timestamp_upper_limit: int, minimum_bid_price: float) -> Iterable[Bid]:
    return filter(lambda bid: bid.auction_id == auction_id and bid.timestamp <= timestamp_upper_limit and bid.price >= minimum_bid_price, bids)

def auction_output(bids: Iterable[Bid], volume_limit: float) -> AuctionOutput:
    sorted_bids = sorted(bids, key = lambda bid: bid.price, reverse = True)
    accumulated_budget = accumulate(sorted_bids, lambda acc, bid: acc-bid.volume, initial=volume_limit) #each bid consumes the auction amount limit.
    def fullfiled_volume(bid, budget):
        return BidOutput(bid.bidder, bid.volume, max(min(budget,bid.volume), 0))
    outputs = starmap(fullfiled_volume, zip(sorted_bids, accumulated_budget))
    return AuctionOutput(outputs, sorted_bids)

def auction_price(output: AuctionOutput) -> float:
    sorted_bids = output.sorted_bids
    outputs = output.bid_outputs
    bid, _ = min(filter(lambda x: x[1].amount_fullfiled > 0, zip(sorted_bids, outputs)), key=lambda x: x[0].price)
    return bid.price

def generate_bid_vouchers(output: BidOutput, price: float) -> Iterable[Voucher]:
    not_fullfiled = output.amount_sent - output.amount_fullfiled
    voucher_list = []
    if not_fullfiled != 0:
        voucher_list.append(Voucher(output.bidder, TokenOperation.TRANSFER, not_fullfiled, False))
    if output.amount_fullfiled > 0:
        if price < 1:
            mint_amount = (1 - price)*output.amount_fullfiled//price
            voucher_list.append(Voucher(output.bidder, TokenOperation.TRANSFER, output.amount_fullfiled, True))
            voucher_list.append(Voucher(output.bidder, TokenOperation.MINT, mint_amount, True))
        elif price > 1:
            burn_amount = (price - 1)*output.amount_fullfiled//price
            voucher_list.append(Voucher(output.bidder, TokenOperation.TRANSFER, output.amount_fullfiled - burn_amount, True))
            voucher_list.append(Voucher("dapp_address", TokenOperation.BURN, burn_amount, True))
    return voucher_list

def auction_vouchers(outputs: Iterable[BidOutput], price: float) -> Iterable[Voucher]:
    return chain(map(lambda output: generate_bid_vouchers(output, price), outputs))

