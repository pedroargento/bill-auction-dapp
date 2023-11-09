from collections.abc import Iterable
from itertools import accumulate, starmap, chain, groupby
from typing import NamedTuple, NewType
from enum import Enum


Address = NewType("Address", str)


class Mine(NamedTuple):
    owner: Address
    erc20_address: Address


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
    bidder: Address


class BidOutput(NamedTuple):
    bidder: Address
    amount_sent: float
    amount_fullfiled: float


class AuctionOutput(NamedTuple):
    bid_outputs: Iterable[BidOutput]
    sorted_bids: Iterable[Bid]


FunctionCall = Enum("FunctionCall", ["TRANSFER", "MINT"])


class Voucher(NamedTuple):
    target_contract: Address
    function_call: FunctionCall
    to: Address
    amount: float
    timestamp_locked: bool


def filter_bids(
    bids: Iterable[Bid],
    auction_id: str,
    timestamp_upper_limit: int,
    minimum_bid_price: float,
) -> Iterable[Bid]:
    return filter(
        lambda bid: bid.auction_id == auction_id
        and bid.timestamp <= timestamp_upper_limit
        and bid.price >= minimum_bid_price,
        bids,
    )


def auction_output(bids: Iterable[Bid], volume_limit: float) -> AuctionOutput:
    sorted_bids = sorted(bids, key=lambda bid: bid.price, reverse=True)
    accumulated_budget = accumulate(
        sorted_bids, lambda acc, bid: acc - bid.volume, initial=volume_limit
    )  # each bid consumes the auction amount limit.

    def fullfiled_volume(bid, budget):
        return BidOutput(bid.bidder, bid.volume, max(min(budget, bid.volume), 0))

    outputs = starmap(fullfiled_volume, zip(sorted_bids, accumulated_budget))
    return AuctionOutput(outputs, sorted_bids)


def auction_price(output: AuctionOutput) -> float:
    sorted_bids = output.sorted_bids
    outputs = output.bid_outputs
    bid, _ = min(
        filter(lambda x: x[1].amount_fullfiled > 0, zip(sorted_bids, outputs)),
        key=lambda x: x[0].price,
    )
    return bid.price


def generate_bid_vouchers(output: BidOutput, price: float) -> Iterable[Voucher]:
    not_fullfiled = output.amount_sent - output.amount_fullfiled
    mint_amount = max((1 - price) * output.amount_fullfiled // price, 0)
    burn_amount = max((price - 1) * output.amount_fullfiled // price, 0)
    return_voucher = Voucher(
        Address("token_contract"),
        FunctionCall.TRANSFER,
        output.bidder,
        not_fullfiled,
        timestamp_locked=False,
    )
    bid_portion_voucher = Voucher(
        Address("token_contract"),
        FunctionCall.TRANSFER,
        to=output.bidder,
        amount=output.amount_fullfiled - burn_amount,
        timestamp_locked=True,
    )
    mint_voucher = Voucher(
        Address("mine_contract"),
        FunctionCall.MINT,
        to=output.bidder,
        amount=mint_amount,
        timestamp_locked=True,
    )
    burn_voucher = Voucher(
        Address("token_contract"),
        FunctionCall.TRANSFER,
        to=Address("mine_contract"),
        amount=burn_amount,
        timestamp_locked=True,
    )
    return filter(
        lambda voucher: voucher.amount > 0,
        [return_voucher, bid_portion_voucher, mint_voucher, burn_voucher],
    )


def auction_vouchers(outputs: Iterable[BidOutput], price: float) -> Iterable[Voucher]:
    return chain(map(lambda output: generate_bid_vouchers(output, price), outputs))


def aggregate_vouchers(vouchers: Iterable[Voucher]) -> Iterable[Voucher]:
    voucher_key = lambda voucher: (
        voucher.target_contract,
        voucher.function_call,
        voucher.to,
        voucher.timestamp_locked,
    )
    sorted_vouchers = sorted(vouchers, key=voucher_key)
    grouped_vouchers = groupby(sorted_vouchers, key=voucher_key)
    return [
        Voucher(
            target_contract=key[0],
            function_call=key[1],
            to=key[2],
            timestamp_locked=key[3],
            amount=sum((voucher.amount for voucher in group)),
        )
        for key, group in grouped_vouchers
    ]
