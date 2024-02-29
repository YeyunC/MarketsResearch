import matplotlib.pyplot as plt

from DataAPI.cryptoCompare import cryptoCompareApi

__dataAPI = cryptoCompareApi()

data = __dataAPI.load_annual_hourly_ohlc_data(mode='fundingrate', instrument='BTC-USDT-VANILLA-PERPETUAL',
                                              market='binance', end_year=2024)

data = data.set_index('TIMESTAMP').resample('1D').first()

fig, ax = plt.subplots(figsize=(9, 4))

# ax.yaxis.set_major_formatter(FormatStrFormatter('.2%'))
# fmt = '%.1f%%'  # Format you want the ticks, e.g. '40%'
# yticks = mtick.FormatStrFormatter(fmt)
# ax.yaxis.set_major_formatter(yticks)


# for i in ['total_pnl', 'unrealized_pnl', 'realized_pnl']:
ax.plot(data.index, data['CLOSE'])

ax.axhline(0, color='black', linestyle='--')

vals = ax.get_yticks()
ax.set_yticklabels([f'{(x * 10000):.0f} bps' for x in vals])

plt.title('BTC-USDT Funding Rate')
plt.legend()
# plt.ylabel('Cummulative PnL in %')
plt.tight_layout()
plt.show()

plt.tight_layout()
plt.show()

print(data)
