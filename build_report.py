#!/usr/bin/env python3
"""Build the final HTML report from all collected data."""

import json
import os
from collections import defaultdict

def load_data():
    with open('data/sells_data.json') as f:
        vibestr_gvc = json.load(f)
    with open('data/stoked_data.json') as f:
        stoked = json.load(f)
    with open('data/moods_data.json') as f:
        moods = json.load(f)
    return vibestr_gvc, stoked, moods

def build_report():
    vibestr_gvc, stoked, moods = load_data()

    wallets = ['IKZ1', 'DGMD22', 'EraOfVibes', 'Extra25', 'InvestmentFund1']

    # Process VIBESTR
    vibestr_data = [r for r in vibestr_gvc if r['token'] == 'VIBESTR']
    vibestr_sells = [r for r in vibestr_data if r['type'] == 'sell' and r['value_eth'] > 0]
    vibestr_buys = [r for r in vibestr_data if r['type'] == 'buy' and r['value_eth'] > 0]

    # Process GVC - only count as sell if ETH was received
    gvc_data = [r for r in vibestr_gvc if r['token'] == 'GVC']
    gvc_real_sells = [r for r in gvc_data if r['type'] == 'sell' and r['value_eth'] > 0]
    gvc_transfers = [r for r in gvc_data if r['type'] == 'sell' and r['value_eth'] == 0]
    gvc_buys = [r for r in gvc_data if r['type'] == 'buy' and r['value_eth'] > 0]

    # Process STOKED - only real sells
    stoked_real = [r for r in stoked if r['value_eth'] > 0]
    stoked_usdg = [r for r in stoked if r['value_eth'] == 0 and r.get('value_usd', 0) > 0]
    stoked_transfers = [r for r in stoked if r['value_eth'] == 0 and r.get('value_usd', 0) == 0]

    # Calculate totals
    vibestr_sell_eth = sum(r['value_eth'] for r in vibestr_sells)
    vibestr_buy_eth = sum(r['value_eth'] for r in vibestr_buys)
    gvc_sell_eth = sum(r['value_eth'] for r in gvc_real_sells)
    gvc_buy_eth = sum(r['value_eth'] for r in gvc_buys)
    gvc_nft_sold = sum(int(r['amount']) for r in gvc_real_sells)
    gvc_nft_transferred = sum(int(r['amount']) for r in gvc_transfers)
    stoked_sell_eth = sum(r['value_eth'] for r in stoked_real)
    stoked_usdg_total = sum(r.get('value_usd', 0) for r in stoked_usdg)

    # Process MOODS
    moods_sells = [r for r in moods if r['type'] == 'sell']
    moods_sell_eth = sum(r['value_eth'] for r in moods_sells)

    # OTC (off-chain) sales
    otc_sales = [
        {'buyer': 'KillerNiz', 'amount': 10, 'price': 0.2, 'total': 2.0, 'token': 'VIBESTR'},
        {'buyer': 'Joafen', 'amount': 40, 'price': 0.2, 'total': 8.0, 'token': 'VIBESTR'},
    ]
    otc_eth = sum(s['total'] for s in otc_sales)

    total_eth_out = vibestr_sell_eth + gvc_sell_eth + stoked_sell_eth + moods_sell_eth + otc_eth
    total_eth_in = vibestr_buy_eth + gvc_buy_eth

    # Per-wallet breakdown
    def wallet_rows(token_name, data_list, is_nft=False, has_usdg=False):
        rows = ''
        for wn in wallets:
            sells = [r for r in data_list if r.get('wallet_name') == wn and r['type'] == 'sell' and r['value_eth'] > 0]
            buys = [r for r in data_list if r.get('wallet_name') == wn and r['type'] == 'buy' and r['value_eth'] > 0]
            transfers = [r for r in data_list if r.get('wallet_name') == wn and r['type'] == 'sell' and r['value_eth'] == 0]

            if not sells and not buys and not transfers:
                continue

            sell_eth = sum(r['value_eth'] for r in sells)
            buy_eth = sum(r['value_eth'] for r in buys)

            if is_nft:
                sell_count = sum(int(r['amount']) for r in sells)
                transfer_count = sum(int(r['amount']) for r in transfers)
                sell_display = f'{sell_count} NFTs'
                transfer_display = f'{transfer_count}' if transfer_count > 0 else '0'
            else:
                sell_count = len(sells)
                sell_display = f'{sell_count}'
                transfer_display = f'{len(transfers)}' if transfers else '0'

            buy_display = f'{len(buys)}' if buys else '0'

            rows += f'''<tr>
                <td>{wn}</td>
                <td class="num">{sell_display}</td>
                <td class="num eth">{sell_eth:.4f}</td>
                <td class="num">{buy_display}</td>
                <td class="num eth">{buy_eth:.4f}</td>
                <td class="num dim">{transfer_display}</td>
            </tr>'''
        return rows

    def stoked_wallet_rows():
        rows = ''
        for wn in wallets:
            ws = [r for r in stoked if r['wallet_name'] == wn]
            real = [r for r in ws if r['value_eth'] > 0]
            usdg = [r for r in ws if r['value_eth'] == 0 and r.get('value_usd', 0) > 0]
            transfers = [r for r in ws if r['value_eth'] == 0 and r.get('value_usd', 0) == 0]

            if not real and not usdg and not transfers:
                continue

            eth_total = sum(r['value_eth'] for r in real)
            usdg_total = sum(r.get('value_usd', 0) for r in usdg)

            rows += f'''<tr>
                <td>{wn}</td>
                <td class="num">{len(real)}</td>
                <td class="num eth">{eth_total:.4f}</td>
                <td class="num">{len(usdg)}</td>
                <td class="num usdg">${usdg_total:.2f}</td>
                <td class="num dim">{len(transfers)}</td>
            </tr>'''
        return rows

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DGMD Wallet Activity Report</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
    background: #0d1117;
    color: #c9d1d9;
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
}}
h1 {{
    color: #58a6ff;
    font-size: 24px;
    margin-bottom: 8px;
}}
.subtitle {{
    color: #8b949e;
    font-size: 14px;
    margin-bottom: 24px;
}}
.cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
}}
.card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px;
}}
.card .label {{
    color: #8b949e;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
.card .value {{
    font-size: 28px;
    font-weight: bold;
    margin-top: 4px;
}}
.card .sub {{
    color: #8b949e;
    font-size: 13px;
    margin-top: 4px;
}}
.eth {{ color: #58a6ff; }}
.sell {{ color: #f85149; }}
.buy {{ color: #3fb950; }}
.usdg {{ color: #d2a8ff; }}
.dim {{ color: #484f58; }}
.section {{
    margin-bottom: 32px;
}}
.section h2 {{
    color: #f0f6fc;
    font-size: 18px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #21262d;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}}
th {{
    text-align: left;
    color: #8b949e;
    font-weight: 500;
    padding: 8px 12px;
    border-bottom: 1px solid #30363d;
    font-size: 12px;
    text-transform: uppercase;
}}
td {{
    padding: 8px 12px;
    border-bottom: 1px solid #21262d;
}}
tr:hover {{ background: #161b22; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.total-row {{
    font-weight: bold;
    border-top: 2px solid #30363d;
}}
.total-row td {{ padding-top: 12px; }}
.note {{
    background: #161b22;
    border-left: 3px solid #d29922;
    padding: 12px 16px;
    font-size: 13px;
    color: #8b949e;
    margin-top: 16px;
    border-radius: 0 6px 6px 0;
}}
.note strong {{ color: #d29922; }}
.wallets {{
    font-size: 12px;
    color: #484f58;
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid #21262d;
}}
.wallets code {{
    background: #161b22;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 11px;
}}
</style>
</head>
<body>
<h1>DGMD Wallet Activity Report</h1>
<p class="subtitle">All-time activity across 5 tracked wallets &mdash; VIBESTR, GVC NFTs, MOODS NFTs, STOKED</p>

<div class="cards">
    <div class="card">
        <div class="label">Total ETH Out (Sells)</div>
        <div class="value sell">{total_eth_out:.2f} ETH</div>
        <div class="sub">VIBESTR + GVC + MOODS + STOKED + OTC</div>
    </div>
    <div class="card">
        <div class="label">Total ETH In (Buys)</div>
        <div class="value buy">{total_eth_in:.2f} ETH</div>
        <div class="sub">VIBESTR + GVC buys only</div>
    </div>
    <div class="card">
        <div class="label">Net ETH Flow</div>
        <div class="value {'sell' if (total_eth_out - total_eth_in) > 0 else 'buy'}">{total_eth_out - total_eth_in:+.2f} ETH</div>
        <div class="sub">{'Extracted' if (total_eth_out - total_eth_in) > 0 else 'Invested'} net</div>
    </div>
    <div class="card">
        <div class="label">GVC NFTs Sold</div>
        <div class="value eth">{gvc_nft_sold}</div>
        <div class="sub">+ {gvc_nft_transferred} plain transfers</div>
    </div>
</div>

<div class="section">
    <h2>VIBESTR Token</h2>
    <table>
        <thead>
            <tr>
                <th>Wallet</th>
                <th class="num">Sells</th>
                <th class="num">ETH Received</th>
                <th class="num">Buys</th>
                <th class="num">ETH Spent</th>
                <th class="num">Transfers</th>
            </tr>
        </thead>
        <tbody>
            {wallet_rows('VIBESTR', vibestr_data)}
            <tr class="total-row">
                <td>TOTAL</td>
                <td class="num">{len(vibestr_sells)}</td>
                <td class="num eth">{vibestr_sell_eth:.4f}</td>
                <td class="num">{len(vibestr_buys)}</td>
                <td class="num eth">{vibestr_buy_eth:.4f}</td>
                <td class="num dim">{len([r for r in vibestr_data if r['type'] == 'sell' and r['value_eth'] == 0])}</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="section">
    <h2>GVC NFTs</h2>
    <table>
        <thead>
            <tr>
                <th>Wallet</th>
                <th class="num">NFTs Sold</th>
                <th class="num">ETH Received</th>
                <th class="num">Buys</th>
                <th class="num">ETH Spent</th>
                <th class="num">Transfers</th>
            </tr>
        </thead>
        <tbody>
            {wallet_rows('GVC', gvc_data, is_nft=True)}
            <tr class="total-row">
                <td>TOTAL</td>
                <td class="num">{gvc_nft_sold} NFTs</td>
                <td class="num eth">{gvc_sell_eth:.4f}</td>
                <td class="num">{len(gvc_buys)}</td>
                <td class="num eth">{gvc_buy_eth:.4f}</td>
                <td class="num dim">{gvc_nft_transferred}</td>
            </tr>
        </tbody>
    </table>
    <div class="note">
        <strong>Note:</strong> Only NFT sales where ETH was received are counted as "sells."
        Plain transfers (wallet-to-wallet, Cryo Chamber swaps) are excluded from sell totals.
    </div>
</div>

<div class="section">
    <h2>STOKED Token (Robinhood Chain)</h2>
    <table>
        <thead>
            <tr>
                <th>Wallet</th>
                <th class="num">ETH Sells</th>
                <th class="num">ETH Received</th>
                <th class="num">USDG Sells</th>
                <th class="num">USDG Received</th>
                <th class="num">Transfers</th>
            </tr>
        </thead>
        <tbody>
            {stoked_wallet_rows()}
            <tr class="total-row">
                <td>TOTAL</td>
                <td class="num">{len(stoked_real)}</td>
                <td class="num eth">{stoked_sell_eth:.4f}</td>
                <td class="num">{len(stoked_usdg)}</td>
                <td class="num usdg">${stoked_usdg_total:.2f}</td>
                <td class="num dim">{len(stoked_transfers)}</td>
            </tr>
        </tbody>
    </table>
    <div class="note">
        <strong>Note:</strong> STOKED was obtained by swapping 80 GVC for 240 MOODS via "Cryo Chamber" &mdash; no ETH was spent buying STOKED.
        Some sells routed to USDG stablecoin instead of ETH.
    </div>
</div>

<div class="section">
    <h2>MOODS NFTs (Robinhood Chain)</h2>
    <table>
        <thead>
            <tr>
                <th>Wallet</th>
                <th class="num">NFTs Sold</th>
                <th class="num">ETH Received</th>
                <th>Buyers</th>
            </tr>
        </thead>
        <tbody>
            {''.join(f"""<tr>
                <td>DGMD22</td>
                <td class="num">1</td>
                <td class="num eth">{s['value_eth']:.4f}</td>
                <td>{s['buyer']}</td>
            </tr>""" for s in moods_sells)}
            <tr class="total-row">
                <td>TOTAL</td>
                <td class="num">{len(moods_sells)} NFTs</td>
                <td class="num eth">{moods_sell_eth:.4f}</td>
                <td></td>
            </tr>
        </tbody>
    </table>
    <div class="note">
        <strong>Note:</strong> MOODS were obtained by swapping GVC NFTs in the "Cryo Chamber" (1 GVC = 3 MOODS).
        Most MOODS were swapped for STOKED via the ANVIL. Only direct sales for ETH/WETH are listed here.
        Data sourced from OpenSea (activity after Aug 27, 2025). Only DGMD22 wallet had MOODS sales.
    </div>
</div>

<div class="section">
    <h2>OTC (Off-Chain) Sales</h2>
    <table>
        <thead>
            <tr>
                <th>Token</th>
                <th>Buyer</th>
                <th class="num">Amount</th>
                <th class="num">Price (ETH)</th>
                <th class="num">Total ETH</th>
            </tr>
        </thead>
        <tbody>
            {''.join(f"""<tr>
                <td>{s['token']}</td>
                <td>{s['buyer']}</td>
                <td class="num">{s['amount']}</td>
                <td class="num">{s['price']:.1f}</td>
                <td class="num eth">{s['total']:.1f}</td>
            </tr>""" for s in otc_sales)}
            <tr class="total-row">
                <td colspan="4">TOTAL</td>
                <td class="num eth">{otc_eth:.1f}</td>
            </tr>
        </tbody>
    </table>
    <div class="note">
        <strong>Note:</strong> These sales happened off-chain (not visible on Etherscan).
        50 VIBESTR sold OTC at 0.2 ETH each = 10 ETH total.
    </div>
</div>

<div class="wallets">
    <strong>Tracked Wallets:</strong><br>
    IKZ1: <code>0xb206a73f101071f7a5027275ef52f827b2ea2b11</code><br>
    DGMD22: <code>0x2d13c884c4c418664abb1b4a7f491dd89247e42e</code><br>
    EraOfVibes: <code>0x662307a93bce119539a81408186bba28f01613cf</code><br>
    Extra25: <code>0x83e574af1bf5813f8552d434b213548e6bd4f35d</code><br>
    InvestmentFund1: <code>0xa1862a515fe0d692392fd1e51d7aeab674a6864b</code>
</div>
</body>
</html>'''

    os.makedirs('public', exist_ok=True)
    with open('public/index.html', 'w') as f:
        f.write(html)
    print('Report saved to public/index.html')

if __name__ == '__main__':
    build_report()
