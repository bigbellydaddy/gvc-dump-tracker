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

    # Wallet rows for the table
    wallet_rows = ''
    for wn in WALLETS:
        s = stats[wn]
        addr = WALLET_ADDRS[wn][:6] + '...' + WALLET_ADDRS[wn][-4:]
        w_in = s['vib_buy'] + s['gvc_buy']
        w_out = s['vib_sell'] + s['gvc_sell'] + s['stk_eth'] + s['moods_eth']
        w_net = w_out - w_in
        w_in_usd = s['vib_buy_usd'] + s['gvc_buy_usd']
        w_out_usd = s['vib_sell_usd'] + s['gvc_sell_usd'] + s['stk_usd'] + s['moods_usd']
        w_net_usd = w_out_usd - w_in_usd

        wallet_rows += f'''<tr>
            <td class="wallet-name">{wn}<span class="addr">{addr}</span></td>
            <td class="num buy">{s['vib_buy']:.2f}</td>
            <td class="num sell">{s['vib_sell']:.2f}</td>
            <td class="num buy">{s['gvc_buy']:.2f}</td>
            <td class="num sell">{s['gvc_sell']:.2f}</td>
            <td class="num sell">{s['stk_eth']:.2f}</td>
            <td class="num sell">{s['moods_eth']:.2f}</td>
            <td class="num {'profit' if w_net > 0 else 'loss'}">{w_net:+.2f}<span class="usd-sub">{fmt_usd(abs(w_net_usd))}</span></td>
        </tr>'''

    # Token P&L bars
    vib_net = t_vib_sell + OTC_ETH - t_vib_buy
    vib_net_usd = t_vib_sell_usd + otc_usd - t_vib_buy_usd
    gvc_net = t_gvc_sell - t_gvc_buy
    gvc_net_usd = t_gvc_sell_usd - t_gvc_buy_usd

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DGMD Wallet Tracker</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #0a0e14;
    color: #c9d1d9;
    padding: 24px 28px;
    max-width: 1200px;
    margin: 0 auto;
}}

/* Header */
.hdr {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 20px; }}
h1 {{ color: #fff; font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }}
.ts {{ color: #3d4450; font-size: 10px; }}

/* Hero cards row */
.hero {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px; }}
.hero-card {{
    background: #111820;
    border: 1px solid #1c2432;
    border-radius: 10px;
    padding: 16px 18px;
    position: relative;
    overflow: hidden;
}}
.hero-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}}
.hc-in::before {{ background: #3fb950; }}
.hc-out::before {{ background: #f85149; }}
.hc-net::before {{ background: #58a6ff; }}
.hc-label {{ color: #6e7681; font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 600; }}
.hc-value {{ font-size: 32px; font-weight: 800; margin-top: 4px; letter-spacing: -1px; font-family: 'SF Mono', monospace; }}
.hc-usd {{ font-size: 14px; font-weight: 600; margin-top: 2px; font-family: 'SF Mono', monospace; opacity: 0.7; }}
.hc-sub {{ color: #3d4450; font-size: 10px; margin-top: 2px; }}

/* Token breakdown cards */
.tokens {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 20px; }}
.tk {{
    background: #111820;
    border: 1px solid #1c2432;
    border-radius: 10px;
    padding: 14px;
    text-align: center;
}}
.tk-name {{ color: #58a6ff; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }}
.tk-big {{ font-size: 20px; font-weight: 800; font-family: 'SF Mono', monospace; letter-spacing: -0.5px; }}
.tk-row {{ display: flex; justify-content: space-between; font-size: 11px; margin-top: 4px; font-family: 'SF Mono', monospace; }}
.tk-detail {{ color: #484f58; font-size: 10px; margin-top: 4px; }}
.tk-usd {{ color: #6e7681; font-size: 10px; margin-top: 2px; font-family: 'SF Mono', monospace; }}
.tk-net {{ font-size: 13px; font-weight: 700; margin-top: 6px; font-family: 'SF Mono', monospace; }}

/* Wallet table */
.tbl-wrap {{
    background: #111820;
    border: 1px solid #1c2432;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 20px;
}}
.tbl-title {{ padding: 12px 16px 0; color: #fff; font-size: 13px; font-weight: 700; }}
.tbl-note {{ padding: 2px 16px 0; color: #3d4450; font-size: 10px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
th {{
    text-align: right;
    color: #3d4450;
    font-weight: 600;
    padding: 8px 12px;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid #1c2432;
    white-space: nowrap;
}}
th:first-child {{ text-align: left; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #141c27; }}
.num {{
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-family: 'SF Mono', monospace;
    font-size: 12px;
}}
.wallet-name {{
    font-weight: 600;
    color: #e6edf3;
    white-space: nowrap;
}}
.addr {{ color: #3d4450; font-size: 9px; font-family: 'SF Mono', monospace; margin-left: 6px; }}
.total-row {{ background: #0d1219; font-weight: 700; }}
.total-row td {{ border-top: 2px solid #1c2432; padding-top: 10px; padding-bottom: 10px; }}

/* Colors */
.buy {{ color: #3fb950; }}
.sell {{ color: #f85149; }}
.profit {{ color: #f85149; }}
.loss {{ color: #3fb950; }}
.usd-sub {{ color: #6e7681; font-size: 9px; margin-left: 4px; display: block; font-weight: 400; }}

/* Flow note */
.flow {{
    background: #111820;
    border: 1px solid #1c2432;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 11px;
    color: #484f58;
    margin-bottom: 16px;
    line-height: 1.6;
}}
.flow strong {{ color: #6e7681; }}
.flow .arrow {{ color: #3d4450; }}

/* Footer */
.foot {{ font-size: 9px; color: #2d333b; padding-top: 10px; border-top: 1px solid #1c2432; }}
.foot code {{ font-size: 8px; color: #3d4450; }}

@media (max-width: 900px) {{
    .tokens {{ grid-template-columns: repeat(3, 1fr); }}
    .hero {{ grid-template-columns: 1fr; }}
    body {{ padding: 14px; }}
}}
@media (max-width: 600px) {{
    .tokens {{ grid-template-columns: 1fr 1fr; }}
    table {{ font-size: 10px; }}
    th, td {{ padding: 6px 8px; }}
}}
</style>
</head>
<body>

<div class="hdr">
    <h1>DGMD Wallet Tracker</h1>
    <span class="ts">Updated {now} &middot; 5 wallets tracked</span>
</div>

<!-- Hero cards -->
<div class="hero">
    <div class="hero-card hc-in">
        <div class="hc-label">Total ETH Spent (Buys)</div>
        <div class="hc-value buy">{grand_in:.2f} ETH</div>
        <div class="hc-usd buy">{fmt_usd(grand_in_usd)}</div>
        <div class="hc-sub">VIBESTR + GVC purchases across all wallets</div>
    </div>
    <div class="hero-card hc-out">
        <div class="hc-label">Total ETH Received (Sells)</div>
        <div class="hc-value sell">{grand_out:.2f} ETH</div>
        <div class="hc-usd sell">{fmt_usd(grand_out_usd)}</div>
        <div class="hc-sub">All sells incl. OTC &amp; STOKED</div>
    </div>
    <div class="hero-card hc-net">
        <div class="hc-label">Net P&L</div>
        <div class="hc-value {'sell' if grand_net > 0 else 'buy'}">{grand_net:+.2f} ETH</div>
        <div class="hc-usd {'sell' if grand_net_usd > 0 else 'buy'}">{fmt_usd(abs(grand_net_usd))}</div>
        <div class="hc-sub">{'Spent more than received' if grand_net < 0 else 'Received more than spent'} &middot; USD at time of each tx</div>
    </div>
</div>

<!-- Token breakdown -->
<div class="tokens">
    <div class="tk">
        <div class="tk-name">VIBESTR</div>
        <div class="tk-row"><span class="buy">In: {t_vib_buy:.2f}e</span><span class="sell">Out: {t_vib_sell:.2f}e</span></div>
        <div class="tk-net {'sell' if vib_net > 0 else 'buy'}">Net: {vib_net:+.2f}e</div>
        <div class="tk-usd">~{fmt_usd(abs(vib_net_usd))}</div>
        <div class="tk-detail">{t_vib_sell + OTC_ETH:.2f}e total w/ OTC</div>
    </div>
    <div class="tk">
        <div class="tk-name">GVC</div>
        <div class="tk-row"><span class="buy">In: {t_gvc_buy:.2f}e</span><span class="sell">Out: {t_gvc_sell:.2f}e</span></div>
        <div class="tk-net {'sell' if gvc_net > 0 else 'buy'}">Net: {gvc_net:+.2f}e</div>
        <div class="tk-usd">~{fmt_usd(abs(gvc_net_usd))}</div>
        <div class="tk-detail">{sum(s['gvc_n_buy'] for s in stats.values())} bought / {sum(s['gvc_n_sold'] for s in stats.values())} sold</div>
    </div>
    <div class="tk">
        <div class="tk-name">STOKED</div>
        <div class="tk-big sell">{t_stk_eth:.2f} ETH</div>
        <div class="tk-usd">~{fmt_usd(t_stk_usd)}</div>
        <div class="tk-detail">{sum(s['stk_sells'] for s in stats.values())} sells (incl. USDG &rarr; ETH)</div>
    </div>
    <div class="tk">
        <div class="tk-name">MOODS</div>
        <div class="tk-big sell">{t_moods:.4f} ETH</div>
        <div class="tk-usd">~{fmt_usd(t_moods_usd)}</div>
        <div class="tk-detail">{sum(s['moods_n'] for s in stats.values())} NFTs sold on OpenSea</div>
    </div>
    <div class="tk">
        <div class="tk-name">OTC</div>
        <div class="tk-big sell">{OTC_ETH:.2f} ETH</div>
        <div class="tk-usd">~{fmt_usd(otc_usd)}</div>
        <div class="tk-detail">50 VIBESTR @ 0.2 ETH each</div>
    </div>
</div>

<!-- Per-wallet table -->
<div class="tbl-wrap">
    <div class="tbl-title">Per-Wallet Breakdown</div>
    <div class="tbl-note">All values in ETH &middot; Net column includes USD at time of transaction</div>
    <table>
        <thead>
            <tr>
                <th style="text-align:left">Wallet</th>
                <th>VIBESTR ETH In</th>
                <th>VIBESTR ETH Out</th>
                <th>GVC ETH In</th>
                <th>GVC ETH Out</th>
                <th>STOKED (ETH)</th>
                <th>MOODS (ETH)</th>
                <th>Net (ETH)</th>
            </tr>
        </thead>
        <tbody>
            {wallet_rows}
            <tr class="total-row">
                <td class="wallet-name">TOTAL</td>
                <td class="num buy">{t_vib_buy:.2f}</td>
                <td class="num sell">{t_vib_sell:.2f}</td>
                <td class="num buy">{t_gvc_buy:.2f}</td>
                <td class="num sell">{t_gvc_sell:.2f}</td>
                <td class="num sell">{t_stk_eth:.2f}</td>
                <td class="num sell">{t_moods:.2f}</td>
                <td class="num {'profit' if grand_net > 0 else 'loss'}">{grand_net:+.2f}<span class="usd-sub">{fmt_usd(abs(grand_net_usd))}</span></td>
            </tr>
        </tbody>
    </table>
</div>

<!-- Flow explanation -->
<div class="flow">
    <strong>Token flow:</strong>
    ETH <span class="arrow">&rarr;</span> buy <span class="buy">GVC</span> &amp; <span class="buy">VIBESTR</span>
    <span class="arrow">&rarr;</span> Cryo Chamber (1 GVC = 3 MOODS)
    <span class="arrow">&rarr;</span> some <span class="sell">MOODS sold</span> directly, most MOODS <span class="arrow">&rarr;</span> ANVIL <span class="arrow">&rarr;</span> <span class="sell">STOKED</span> <span class="arrow">&rarr;</span> sold for ETH.
    No ETH was spent buying STOKED or MOODS. OTC: 50 VIBESTR sold off-chain for {OTC_ETH:.0f} ETH.
    USD values calculated using historical ETH price at time of each transaction (via DeFiLlama).
</div>

<div class="foot">
    <strong>Wallets:</strong>
    {' &middot; '.join(f'{wn}: <code>{WALLET_ADDRS[wn][:8]}...</code>' for wn in WALLETS)}
    <br>Sources: Etherscan V2 (VIBESTR, GVC), Robinhood Chain (STOKED), OpenSea (MOODS), Manual (OTC)
    <br>USD prices: DeFiLlama historical ETH/USD at time of each transaction
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
