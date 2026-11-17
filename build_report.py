#!/usr/bin/env python3
"""Build a clean infographic-style HTML report from all collected data."""

import json
import os
from datetime import datetime

WALLETS = ['IKZ1', 'DGMD22', 'EraOfVibes', 'Extra25', 'InvestmentFund1']
WALLET_ADDRS = {
    'IKZ1': '0xb206a73f101071f7a5027275ef52f827b2ea2b11',
    'DGMD22': '0x2d13c884c4c418664abb1b4a7f491dd89247e42e',
    'EraOfVibes': '0x662307a93bce119539a81408186bba28f01613cf',
    'Extra25': '0x83e574af1bf5813f8552d434b213548e6bd4f35d',
    'InvestmentFund1': '0xa1862a515fe0d692392fd1e51d7aeab674a6864b',
}

OTC_SALES = [
    {'buyer': 'KillerNiz', 'amount': 10, 'price': 0.2, 'total': 2.0, 'token': 'VIBESTR'},
    {'buyer': 'Joafen', 'amount': 40, 'price': 0.2, 'total': 8.0, 'token': 'VIBESTR'},
]
OTC_ETH = sum(s['total'] for s in OTC_SALES)

# Current holdings (checked on-chain 2026-11-17)
HOLDINGS_GVC = 178          # 73 DGMD22 + 105 vault (0x8972...54ca)
HOLDINGS_VIBESTR = 10013424 # ~10M in DGMD22
ETH_PRICE_USD = 1815       # approx current
VIBESTR_PRICE_USD = 0.0005644  # OpenSea

# GVC values from OpenSea per-NFT top offers (2026-11-17)
# Vault: actual per-NFT top offers scraped from OpenSea
# DGMD22: mostly floor/commons, using collection top offer $253.21 each
GVC_VAULT_VALUE_USD = 42577.06   # 105 NFTs, actual per-NFT offers
GVC_DGMD22_VALUE_USD = 18484.33  # 73 NFTs x $253.21 collection offer
GVC_TOTAL_VALUE_USD = GVC_VAULT_VALUE_USD + GVC_DGMD22_VALUE_USD  # $61,061

# STOKED data (Robinhood chain - can't auto-fetch, Cloudflare blocked)
# Dates are approximate for USD calculation
STOKED_DATA = [
    {'wallet_name': 'IKZ1', 'value_eth': 0.3866, 'amount': 3300000, 'date': '2026-10-15'},
    {'wallet_name': 'IKZ1', 'value_eth': 0.4129, 'amount': 3300000, 'date': '2026-10-16'},
    {'wallet_name': 'IKZ1', 'value_eth': 0.2123, 'amount': 1600000, 'date': '2026-10-17'},
    {'wallet_name': 'IKZ1', 'value_eth': 0.2736, 'amount': 2000000, 'date': '2026-10-18'},
    {'wallet_name': 'IKZ1', 'value_eth': 0.3439, 'amount': 2600000, 'date': '2026-10-19'},
    {'wallet_name': 'IKZ1', 'value_eth': 0.2815, 'amount': 2000000, 'date': '2026-10-20'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.2901, 'amount': 2800000, 'date': '2026-10-15'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.1502, 'amount': 1400000, 'date': '2026-10-16'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.1946, 'amount': 1700000, 'date': '2026-10-17'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.2493, 'amount': 2200000, 'date': '2026-10-18'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.144, 'amount': 1400000, 'date': '2026-11-15'},  # was $263.89 USDG, converted at ~$1,833/ETH
    {'wallet_name': 'EraOfVibes', 'value_eth': 0.2114, 'amount': 1500000, 'date': '2026-11-11'},
    {'wallet_name': 'EraOfVibes', 'value_eth': 0.2184, 'amount': 1500000, 'date': '2026-11-11'},
    {'wallet_name': 'EraOfVibes', 'value_eth': 0.2351, 'amount': 1600000, 'date': '2026-11-14'},
    {'wallet_name': 'EraOfVibes', 'value_eth': 0.1717, 'amount': 1100000, 'date': '2026-11-14'},
    {'wallet_name': 'EraOfVibes', 'value_eth': 0.2118, 'amount': 1400000, 'date': '2026-11-14'},
    {'wallet_name': 'EraOfVibes', 'value_eth': 0.2666, 'amount': 1800000, 'date': '2026-11-15'},
    {'wallet_name': 'Extra25', 'value_eth': 0.6373, 'amount': 4600000, 'date': '2026-10-15'},
    {'wallet_name': 'Extra25', 'value_eth': 0.1623, 'amount': 1100000, 'date': '2026-10-16'},
    {'wallet_name': 'Extra25', 'value_eth': 0.2171, 'amount': 1400000, 'date': '2026-10-17'},
    {'wallet_name': 'Extra25', 'value_eth': 0.2940, 'amount': 1800000, 'date': '2026-10-18'},
    {'wallet_name': 'InvestmentFund1', 'value_eth': 0.7757, 'amount': 4000000, 'date': '2026-10-15'},
    {'wallet_name': 'InvestmentFund1', 'value_eth': 0.7943, 'amount': 4000000, 'date': '2026-10-16'},
    {'wallet_name': 'InvestmentFund1', 'value_eth': 0.9677, 'amount': 4500000, 'date': '2026-10-17'},
    {'wallet_name': 'InvestmentFund1', 'value_eth': 0.7856, 'amount': 3100000, 'date': '2026-10-18'},
]

# MOODS data (OpenSea, Robinhood chain - scraped manually)
MOODS_DATA = [
    {'wallet_name': 'DGMD22', 'value_eth': 0.15, 'type': 'sell', 'date': '2025-11-09'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.0324, 'type': 'sell', 'date': '2025-11-13'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.0322, 'type': 'sell', 'date': '2025-11-13'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.0322, 'type': 'sell', 'date': '2025-11-14'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.0322, 'type': 'sell', 'date': '2025-11-14'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.06, 'type': 'sell', 'date': '2025-11-14'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.06, 'type': 'sell', 'date': '2025-11-14'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.08, 'type': 'sell', 'date': '2025-11-16'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.20, 'type': 'sell', 'date': '2025-11-16'},
    {'wallet_name': 'DGMD22', 'value_eth': 0.15, 'type': 'sell', 'date': '2025-11-16'},
]


def load_data():
    with open('data/sells_data.json') as f:
        vibestr_gvc = json.load(f)
    prices = {}
    if os.path.exists('data/eth_prices.json'):
        with open('data/eth_prices.json') as f:
            prices = json.load(f)
    return vibestr_gvc, STOKED_DATA, MOODS_DATA, prices


def get_price(prices, date_str):
    """Get ETH/USD price for a date, falling back to nearest available."""
    d = date_str[:10]
    if d in prices:
        return prices[d]
    # Find nearest date
    all_dates = sorted(prices.keys())
    if not all_dates:
        return 0
    for ad in all_dates:
        if ad >= d:
            return prices[ad]
    return prices[all_dates[-1]]


def fmt_usd(v):
    if v >= 1000:
        return f'${v:,.0f}'
    return f'${v:.0f}'


def build_report():
    vibestr_gvc, stoked, moods, prices = load_data()
    now = datetime.utcnow().strftime('%b %d, %Y %H:%M UTC')

    # Compute all stats with USD
    stats = {}
    for wn in WALLETS:
        # STOKED
        sd = [r for r in stoked if r.get('wallet_name') == wn]
        stk_eth = sum(r['value_eth'] for r in sd)
        stk_usd = sum(r['value_eth'] * get_price(prices, r.get('date', '2026-10-15')) for r in sd)
        stk_sells = len(sd)

        # VIBESTR
        vd = [r for r in vibestr_gvc if r['token'] == 'VIBESTR' and r.get('wallet_name') == wn]
        vib_buy = sum(r['value_eth'] for r in vd if r['type'] == 'buy' and r['value_eth'] > 0)
        vib_sell = sum(r['value_eth'] for r in vd if r['type'] == 'sell' and r['value_eth'] > 0)
        vib_buy_usd = sum(r['value_eth'] * get_price(prices, r.get('date', '')) for r in vd if r['type'] == 'buy' and r['value_eth'] > 0)
        vib_sell_usd = sum(r['value_eth'] * get_price(prices, r.get('date', '')) for r in vd if r['type'] == 'sell' and r['value_eth'] > 0)
        vib_n_buy = len([r for r in vd if r['type'] == 'buy' and r['value_eth'] > 0])
        vib_n_sell = len([r for r in vd if r['type'] == 'sell' and r['value_eth'] > 0])

        # GVC
        gd = [r for r in vibestr_gvc if r['token'] == 'GVC' and r.get('wallet_name') == wn]
        gvc_buy = sum(r['value_eth'] for r in gd if r['type'] == 'buy' and r['value_eth'] > 0)
        gvc_sell = sum(r['value_eth'] for r in gd if r['type'] == 'sell' and r['value_eth'] > 0)
        gvc_buy_usd = sum(r['value_eth'] * get_price(prices, r.get('date', '')) for r in gd if r['type'] == 'buy' and r['value_eth'] > 0)
        gvc_sell_usd = sum(r['value_eth'] * get_price(prices, r.get('date', '')) for r in gd if r['type'] == 'sell' and r['value_eth'] > 0)
        gvc_n_buy = len([r for r in gd if r['type'] == 'buy' and r['value_eth'] > 0])
        gvc_n_sold = sum(int(r['amount']) for r in gd if r['type'] == 'sell' and r['value_eth'] > 0)

        # MOODS
        md = [r for r in moods if r.get('wallet_name') == wn and r['type'] == 'sell']
        moods_eth = sum(r['value_eth'] for r in md)
        moods_usd = sum(r['value_eth'] * get_price(prices, r.get('date', '2025-11-14')) for r in md)
        moods_n = len(md)

        stats[wn] = {
            'stk_eth': stk_eth, 'stk_usd': stk_usd, 'stk_sells': stk_sells,
            'vib_buy': vib_buy, 'vib_sell': vib_sell, 'vib_n_buy': vib_n_buy, 'vib_n_sell': vib_n_sell,
            'vib_buy_usd': vib_buy_usd, 'vib_sell_usd': vib_sell_usd,
            'gvc_buy': gvc_buy, 'gvc_sell': gvc_sell, 'gvc_n_buy': gvc_n_buy, 'gvc_n_sold': gvc_n_sold,
            'gvc_buy_usd': gvc_buy_usd, 'gvc_sell_usd': gvc_sell_usd,
            'moods_eth': moods_eth, 'moods_usd': moods_usd, 'moods_n': moods_n,
        }

    # Totals
    t_stk_eth = sum(s['stk_eth'] for s in stats.values())
    t_stk_usd = sum(s['stk_usd'] for s in stats.values())
    t_vib_buy = sum(s['vib_buy'] for s in stats.values())
    t_vib_sell = sum(s['vib_sell'] for s in stats.values())
    t_vib_buy_usd = sum(s['vib_buy_usd'] for s in stats.values())
    t_vib_sell_usd = sum(s['vib_sell_usd'] for s in stats.values())
    t_gvc_buy = sum(s['gvc_buy'] for s in stats.values())
    t_gvc_sell = sum(s['gvc_sell'] for s in stats.values())
    t_gvc_buy_usd = sum(s['gvc_buy_usd'] for s in stats.values())
    t_gvc_sell_usd = sum(s['gvc_sell_usd'] for s in stats.values())
    t_moods = sum(s['moods_eth'] for s in stats.values())
    t_moods_usd = sum(s['moods_usd'] for s in stats.values())

    # OTC USD estimate (use a mid-range price ~$3,900 for Oct 2025 when OTC likely happened)
    otc_usd = OTC_ETH * get_price(prices, '2025-10-15')

    grand_in = t_vib_buy + t_gvc_buy
    grand_out = t_vib_sell + t_gvc_sell + t_stk_eth + t_moods + OTC_ETH
    grand_net = grand_out - grand_in

    grand_in_usd = t_vib_buy_usd + t_gvc_buy_usd
    grand_out_usd = t_vib_sell_usd + t_gvc_sell_usd + t_stk_usd + t_moods_usd + otc_usd
    grand_net_usd = grand_out_usd - grand_in_usd

    # Holdings value (per-NFT top offers from OpenSea)
    gvc_hold_usd = GVC_TOTAL_VALUE_USD
    gvc_hold_eth = gvc_hold_usd / ETH_PRICE_USD
    vib_hold_usd = HOLDINGS_VIBESTR * VIBESTR_PRICE_USD
    vib_hold_eth = vib_hold_usd / ETH_PRICE_USD
    total_hold_eth = gvc_hold_eth + vib_hold_eth
    total_hold_usd = gvc_hold_usd + vib_hold_usd
    adjusted_net = grand_net + total_hold_eth
    adjusted_net_usd = grand_net_usd + total_hold_usd

    # Build per-asset wallet rows
    def asset_rows(key_in, key_out, key_in_usd=None, key_out_usd=None):
        rows = ''
        for wn in WALLETS:
            s = stats[wn]
            eth_in = s.get(key_in, 0)
            eth_out = s.get(key_out, 0)
            net = eth_out - eth_in
            rows += f'''<tr>
                <td class="wn">{wn}</td>
                <td class="n r">{eth_in:.2f}</td>
                <td class="n g">{eth_out:.2f}</td>
                <td class="n {'g' if net > 0 else 'r'}">{net:+.2f}</td>
            </tr>'''
        return rows

    def sells_only_rows(key_eth, key_usd):
        rows = ''
        for wn in WALLETS:
            s = stats[wn]
            eth = s.get(key_eth, 0)
            if eth > 0:
                rows += f'''<tr>
                    <td class="wn">{wn}</td>
                    <td class="n g">{eth:.4f}</td>
                </tr>'''
        return rows

    vibestr_rows = asset_rows('vib_buy', 'vib_sell')
    gvc_rows = asset_rows('gvc_buy', 'gvc_sell')
    stoked_rows = sells_only_rows('stk_eth', 'stk_usd')
    moods_rows = sells_only_rows('moods_eth', 'moods_usd')

    # Token P&L bars
    vib_net = t_vib_sell + OTC_ETH - t_vib_buy
    vib_net_usd = t_vib_sell_usd + otc_usd - t_vib_buy_usd
    gvc_net = t_gvc_sell - t_gvc_buy
    gvc_net_usd = t_gvc_sell_usd - t_gvc_buy_usd

    # Totals for display
    t_gvc_n_buy = sum(s['gvc_n_buy'] for s in stats.values())
    t_gvc_n_sold = sum(s['gvc_n_sold'] for s in stats.values())
    t_stk_sells = sum(s['stk_sells'] for s in stats.values())
    t_moods_n = sum(s['moods_n'] for s in stats.values())

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DGMD Wallet Tracker</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0d1117;
    color: #b1bac4;
    padding: 12px 16px;
    max-width: 1200px;
    margin: 0 auto;
}}

/* Header row */
.top {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }}
.top h1 {{ color: #e6edf3; font-size: 15px; font-weight: 700; }}
.top .sub {{ color: #484f58; font-size: 9px; }}

/* Summary row */
.sum {{ display: flex; gap: 4px; margin-bottom: 8px; }}
.sc {{
    flex: 1; padding: 6px 10px;
    background: #161b22; border: 1px solid #21262d; border-radius: 6px;
}}
.sc .lb {{ font-size: 8px; color: #484f58; text-transform: uppercase; letter-spacing: 0.4px; font-weight: 600; }}
.sc .vl {{ font-size: 16px; font-weight: 700; font-family: 'SF Mono', ui-monospace, monospace; }}
.sc .us {{ font-size: 9px; color: #484f58; font-family: 'SF Mono', ui-monospace, monospace; }}
.r {{ color: #f85149; }}
.g {{ color: #3fb950; }}
.b {{ color: #58a6ff; }}

/* 2x2 grid for assets */
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 6px; }}
.asset {{
    border: 1px solid #21262d; border-radius: 6px; overflow: hidden;
}}
.ah {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 6px 10px; background: #161b22; border-bottom: 1px solid #21262d;
}}
.ah .nm {{ font-size: 11px; font-weight: 700; color: #e6edf3; }}
.ah .tg {{ font-size: 8px; color: #484f58; background: #21262d; padding: 1px 6px; border-radius: 8px; }}
.ast {{
    display: flex; gap: 12px; padding: 6px 10px;
    background: #0d1117; border-bottom: 1px solid #21262d; flex-wrap: wrap;
}}
.ai .al {{ font-size: 7px; color: #484f58; text-transform: uppercase; letter-spacing: 0.3px; }}
.ai .av {{ font-size: 12px; font-weight: 700; font-family: 'SF Mono', ui-monospace, monospace; }}
.ai .au {{ font-size: 8px; color: #484f58; font-family: 'SF Mono', ui-monospace, monospace; }}

/* Tables */
.asset table {{ width: 100%; border-collapse: collapse; }}
.asset th {{
    text-align: right; font-size: 8px; color: #484f58; font-weight: 600;
    padding: 3px 10px; text-transform: uppercase; letter-spacing: 0.3px;
    background: #0d1117; border-bottom: 1px solid #21262d;
}}
.asset th:first-child {{ text-align: left; }}
.asset td {{ padding: 1px 10px; border-bottom: 1px solid #161b22; }}
.wn {{ font-weight: 600; color: #c9d1d9; font-size: 10px; }}
.n {{ text-align: right; font-family: 'SF Mono', ui-monospace, monospace; font-size: 10px; font-variant-numeric: tabular-nums; }}
.asset .tot td {{ background: #161b22; font-weight: 700; border-top: 1px solid #21262d; }}

/* Holdings row */
.holds {{ display: flex; gap: 4px; margin-bottom: 4px; }}
.hc {{
    flex: 1; padding: 6px 10px;
    background: #161b22; border: 1px solid #1f6feb33; border-radius: 6px;
}}
.hc .lb {{ font-size: 8px; color: #58a6ff; text-transform: uppercase; letter-spacing: 0.4px; font-weight: 600; }}
.hc .vl {{ font-size: 14px; font-weight: 700; color: #e6edf3; font-family: 'SF Mono', ui-monospace, monospace; }}
.hc .dt {{ font-size: 9px; color: #484f58; }}

/* Footer */
.foot {{ font-size: 8px; color: #30363d; line-height: 1.5; }}
.foot code {{ font-size: 7px; color: #484f58; }}
</style>
</head>
<body>

<div class="top">
    <h1>DGMD Wallet Tracker</h1>
    <span class="sub">5 wallets &middot; {now}</span>
</div>

<!-- Summary -->
<div class="sum">
    <div class="sc"><div class="lb">ETH Spent</div><div class="vl r">{grand_in:.2f}</div><div class="us">{fmt_usd(grand_in_usd)}</div></div>
    <div class="sc"><div class="lb">ETH Received</div><div class="vl g">{grand_out:.2f}</div><div class="us">{fmt_usd(grand_out_usd)}</div></div>
    <div class="sc"><div class="lb">Realized P&L</div><div class="vl {'g' if grand_net > 0 else 'r'}">{grand_net:+.2f}</div><div class="us">{fmt_usd(abs(grand_net_usd))}</div></div>
    <div class="sc"><div class="lb">Adj. P&L (w/ holdings)</div><div class="vl {'g' if adjusted_net > 0 else 'r'}">{adjusted_net:+.2f}</div><div class="us">{fmt_usd(abs(adjusted_net_usd))}</div></div>
</div>

<!-- 2x2 Asset Grid -->
<div class="grid">

<!-- VIBESTR -->
<div class="asset">
    <div class="ah"><span class="nm">VIBESTR</span><span class="tg">ERC-20</span></div>
    <div class="ast">
        <div class="ai"><div class="al">ETH In</div><div class="av r">{t_vib_buy:.2f}</div><div class="au">{fmt_usd(t_vib_buy_usd)}</div></div>
        <div class="ai"><div class="al">ETH Out</div><div class="av g">{t_vib_sell:.2f}</div><div class="au">{fmt_usd(t_vib_sell_usd)}</div></div>
        <div class="ai"><div class="al">OTC</div><div class="av g">{OTC_ETH:.0f}</div><div class="au">50 @ 0.2e</div></div>
        <div class="ai"><div class="al">Net</div><div class="av {'g' if vib_net > 0 else 'r'}">{vib_net:+.2f}</div></div>
    </div>
    <table>
        <tr><th>Wallet</th><th>In</th><th>Out</th><th>Net</th></tr>
        {vibestr_rows}
        <tr class="tot"><td class="wn">Total</td><td class="n r">{t_vib_buy:.2f}</td><td class="n g">{t_vib_sell:.2f}</td><td class="n {'g' if t_vib_sell - t_vib_buy > 0 else 'r'}">{t_vib_sell - t_vib_buy:+.2f}</td></tr>
    </table>
</div>

<!-- GVC -->
<div class="asset">
    <div class="ah"><span class="nm">GVC</span><span class="tg">ERC-721 NFT</span></div>
    <div class="ast">
        <div class="ai"><div class="al">ETH In ({t_gvc_n_buy})</div><div class="av r">{t_gvc_buy:.2f}</div><div class="au">{fmt_usd(t_gvc_buy_usd)}</div></div>
        <div class="ai"><div class="al">ETH Out ({t_gvc_n_sold})</div><div class="av g">{t_gvc_sell:.2f}</div><div class="au">{fmt_usd(t_gvc_sell_usd)}</div></div>
        <div class="ai"><div class="al">Net</div><div class="av r">{gvc_net:+.2f}</div></div>
    </div>
    <table>
        <tr><th>Wallet</th><th>In</th><th>Out</th><th>Net</th></tr>
        {gvc_rows}
        <tr class="tot"><td class="wn">Total</td><td class="n r">{t_gvc_buy:.2f}</td><td class="n g">{t_gvc_sell:.2f}</td><td class="n r">{gvc_net:+.2f}</td></tr>
    </table>
</div>

<!-- MOODS -->
<div class="asset">
    <div class="ah"><span class="nm">MOODS</span><span class="tg">NFT &middot; Cryo Chamber</span></div>
    <div class="ast">
        <div class="ai"><div class="al">ETH In</div><div class="av" style="color:#484f58">0</div><div class="au">Free from Cryo</div></div>
        <div class="ai"><div class="al">ETH Out ({t_moods_n} sold)</div><div class="av g">{t_moods:.4f}</div><div class="au">{fmt_usd(t_moods_usd)}</div></div>
    </div>
    <table>
        <tr><th>Wallet</th><th>ETH Out</th></tr>
        {moods_rows}
        <tr class="tot"><td class="wn">Total</td><td class="n g">{t_moods:.4f}</td></tr>
    </table>
</div>

<!-- STOKED -->
<div class="asset">
    <div class="ah"><span class="nm">STOKED</span><span class="tg">Token &middot; ANVIL</span></div>
    <div class="ast">
        <div class="ai"><div class="al">ETH In</div><div class="av" style="color:#484f58">0</div><div class="au">Free from ANVIL</div></div>
        <div class="ai"><div class="al">ETH Out ({t_stk_sells} sells)</div><div class="av g">{t_stk_eth:.2f}</div><div class="au">{fmt_usd(t_stk_usd)}</div></div>
    </div>
    <table>
        <tr><th>Wallet</th><th>ETH Out</th></tr>
        {stoked_rows}
        <tr class="tot"><td class="wn">Total</td><td class="n g">{t_stk_eth:.2f}</td></tr>
    </table>
</div>

</div><!-- /grid -->

<!-- Holdings -->
<div class="holds">
    <div class="hc"><div class="lb">Holds: GVC</div><div class="vl">{HOLDINGS_GVC} NFTs</div><div class="dt">{gvc_hold_eth:.2f}e &middot; {fmt_usd(gvc_hold_usd)} &middot; 73 DGMD22 + 105 vault</div></div>
    <div class="hc"><div class="lb">Holds: VIBESTR</div><div class="vl">{HOLDINGS_VIBESTR:,.0f}</div><div class="dt">{vib_hold_eth:.2f}e &middot; {fmt_usd(vib_hold_usd)} &middot; ~10M in DGMD22</div></div>
</div>

<div class="foot">
    ETH &rarr; buy <span class="g">GVC</span> + <span class="g">VIBESTR</span> &rarr; Cryo (1 GVC = 3 MOODS) &rarr; <span class="r">MOODS/STOKED sold</span>. OTC: 50 VIBESTR for {OTC_ETH:.0f}e.
    <br>{' &middot; '.join(f'{wn}: <code>{WALLET_ADDRS[wn][:8]}...</code>' for wn in WALLETS)} + vault: <code>0x8972e0...</code>
</div>

</body>
</html>'''

    os.makedirs('public', exist_ok=True)
    with open('public/index.html', 'w') as f:
        f.write(html)
    print('Report saved to public/index.html')
    print(f'ETH In: {grand_in:.2f} (${grand_in_usd:,.0f}) | Out: {grand_out:.2f} (${grand_out_usd:,.0f}) | Net: {grand_net:+.2f} (${grand_net_usd:+,.0f})')


if __name__ == '__main__':
    build_report()
