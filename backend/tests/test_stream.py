from app.stream import CoinbaseMarketDataProvider


def test_coinbase_provider_parses_ticker_payload():
    provider = CoinbaseMarketDataProvider()

    tick = provider.tick_from_payload(
        "BTC-USD",
        {
            "price": "6268.48",
            "size": "0.00698254",
            "time": "2020-03-20T00:22:57.833Z",
            "bid": "6265.15",
            "ask": "6267.71",
            "volume": "53602.03940154",
        },
    )

    assert tick.symbol == "BTC-USD"
    assert tick.price == 6268.48
    assert tick.bid == 6265.15
    assert tick.ask == 6267.71
    assert tick.volume == 53602.03940154
    assert tick.source == "coinbase"
