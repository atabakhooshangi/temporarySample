from copytrading.exchange import generate_exchange_client


if __name__ == "__main__":
    exchange_client = generate_exchange_client(
        exchange="bybit",
        credentials=dict(
            api_key="xxx",
            secret="xxx",
            password="",
        ),
        sandbox_mode=True,
    )
    balance_response = exchange_client.get_balance()
    ccxt_response = exchange_client.create_future_order(
        symbol="BTC/USDT:USDT",
        side="sell",
        order_type="limit",
        amount=exchange_client.get_amount(
            100
        ),
        price=48900,
        take_profit=47,
        stop_loss=47000,
        leverage=5,
        reduce_only=False
    )