#!/usr/bin/env python3
"""Build the final HTML report from all collected data."""

import json
import os

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


def load_data():
    with open('data/sells_data.json') as f:
        vibestr_gvc = json.load(f)
    with open('data/stoked_data.json') as f:
        stoked = json.load(f)
    with open('data/moods_data.json') as f:
        moods = json.load(f)
    return vibestr_gvc, stoked, moods


def get_wallet_token_stats(wn, vibestr_gvc, stoked, moods):
    """Get per-token stats for a single wallet."""
    tokens = {}

    # VIBESTR
    vd = [r for r in vibestr_gvc if r['token'] == 'VIBESTR' and r.get('wallet_name') == wn]
    vs = [r for r in vd if r['type'] == 'sell' and r['value_eth'] > 0]
    vb = [r for r in vd if r['type'] == 'buy' and r['value_eth'] > 0]
    tokens['VIBESTR'] = {
        'sells': len(vs), 'sell_eth': sum(r['value_eth'] for r in vs),
        'buys': len(vb), 'buy_eth': sum(r['value_eth'] for r in vb),
        'sell_label': f'{len(vs)} sells',
    }

    # GVC
    gd = [r for r in vibestr_gvc if r['token'] == 'GVC' and r.get('wallet_name') == wn]
    gs = [r for r in gd if r['type'] == 'sell' and r['value_eth'] > 0]
    gb = [r for r in gd if r['type'] == 'buy' and r['value_eth'] > 0]
    nft_sold = sum(int(r['amount']) for r in gs)
    tokens['GVC'] = {
        'sells': nft_sold, 'sell_eth': sum(r['value_eth'] for r in gs),
        'buys': len(gb), 'buy_eth': sum(r['value_eth'] for r in gb),
        'sell_label': f'{nft_sold} NFTs sold',
    }

    # STOKED
    sd = [r for r in stoked if r.get('wallet_name') == wn]
    sr = [r for r in sd if r['value_eth'] > 0]
    su = [r for r in sd if r['value_eth'] == 0 and r.get('value_usd', 0) > 0]
    usdg = sum(r.get('value_usd', 0) for r in su)
    tokens['STOKED'] = {
        'sells': len(sr), 'sell_eth': sum(r['value_eth'] for r in sr),
        'buys': 0, 'buy_eth': 0,
        'sell_label': f'{len(sr)} sells',
        'usdg_sells': len(su), 'usdg_total': usdg,
    }

    # MOODS
    md = [r for r in moods if r.get('wallet_name') == wn and r['type'] == 'sell']
    tokens['MOODS'] = {
        'sells': len(md), 'sell_eth': sum(r['value_eth'] for r in md),
        'buys': 0, 'buy_eth': 0,
        'sell_label': f'{len(md)} NFTs sold',
    }

    return tokens


def build_report():
    vibestr_gvc, stoked, moods = load_data()

    # Compute per-wallet stats
    wallet_stats = {}
    for wn in WALLETS:
        wallet_stats[wn] = get_wallet_token_stats(wn, vibestr_gvc, stoked, moods)

    # Grand totals
    grand_out = sum(
        ws[t]['sell_eth'] for ws in wallet_stats.values() for t in ['VIBESTR', 'GVC', 'STOKED', 'MOODS']
    ) + OTC_ETH
    grand_in = sum(
        ws[t]['buy_eth'] for ws in wallet_stats.values() for t in ['VIBESTR', 'GVC', 'STOKED', 'MOODS']
    )
    grand_usdg = sum(ws['STOKED'].get('usdg_total', 0) for ws in wallet_stats.values())
    net = grand_out - grand_in

    # Token-level totals
    token_totals = {}
    for t in ['VIBESTR', 'GVC', 'STOKED', 'MOODS']:
        token_totals[t] = {
            'sell_eth': sum(ws[t]['sell_eth'] for ws in wallet_stats.values()),
            'buy_eth': sum(ws[t]['buy_eth'] for ws in wallet_stats.values()),
            'sells': sum(ws[t]['sells'] for ws in wallet_stats.values()),
            'buys': sum(ws[t]['buys'] for ws in wallet_stats.values()),
        }

    # Build wallet sections HTML
    wallet_sections = ''
    for wn in WALLETS:
        ws = wallet_stats[wn]
        addr = WALLET_ADDRS[wn]
        w_out = sum(ws[t]['sell_eth'] for t in ['VIBESTR', 'GVC', 'STOKED', 'MOODS'])
        w_in = sum(ws[t]['buy_eth'] for t in ['VIBESTR', 'GVC', 'STOKED', 'MOODS'])
        w_usdg = ws['STOKED'].get('usdg_total', 0)

        rows = ''
        for t in ['VIBESTR', 'GVC', 'STOKED', 'MOODS']:
            ts = ws[t]
            if ts['sell_eth'] == 0 and ts['buy_eth'] == 0 and ts.get('usdg_total', 0) == 0:
                continue
            usdg_cell = ''
            if t == 'STOKED' and ts.get('usdg_total', 0) > 0:
                usdg_cell = f' <span class="usdg">+ ${ts["usdg_total"]:.2f} USDG</span>'
            rows += f'''<tr>
                <td class="token-name">{t}</td>
                <td class="num buy">{ts['buy_eth']:.4f}</td>
                <td class="num">{ts['buys']} buys</td>
                <td class="num sell">{ts['sell_eth']:.4f}{usdg_cell}</td>
                <td class="num">{ts['sell_label']}</td>
            </tr>'''

        usdg_note = f' <span class="usdg">+ ${w_usdg:.2f} USDG</span>' if w_usdg > 0 else ''

        wallet_sections += f'''
<div class="wallet-section">
    <div class="wallet-top">
        <div class="wallet-header">
            <h2>{wn}</h2>
            <code class="wallet-addr">{addr}</code>
        </div>
        <div class="wallet-cards">
            <div class="mini-card">
                <span class="mini-label">ETH In</span>
                <span class="mini-value buy">{w_in:.4f}</span>
            </div>
            <div class="mini-card">
                <span class="mini-label">ETH Out</span>
                <span class="mini-value sell">{w_out:.4f}</span>
            </div>
            <div class="mini-card">
                <span class="mini-label">Net</span>
                <span class="mini-value {'sell' if (w_out - w_in) > 0 else 'buy'}">{w_out - w_in:+.4f}</span>
            </div>
        </div>
    </div>
    <table>
        <thead>
            <tr>
                <th>Token</th>
                <th class="num">ETH In (Buys)</th>
                <th class="num">Details</th>
                <th class="num">ETH Out (Sells)</th>
                <th class="num">Details</th>
            </tr>
        </thead>
        <tbody>
            {rows}
            <tr class="total-row">
                <td>WALLET TOTAL</td>
                <td class="num buy">{w_in:.4f}</td>
                <td></td>
                <td class="num sell">{w_out:.4f}{usdg_note}</td>
                <td></td>
            </tr>
        </tbody>
    </table>
</div>'''

    # Token summary section
    token_summary_rows = ''
    for t in ['VIBESTR', 'GVC', 'MOODS', 'STOKED']:
        tt = token_totals[t]
        extra = ''
        if t == 'STOKED' and grand_usdg > 0:
            extra = f' <span class="usdg">+ ${grand_usdg:.2f} USDG</span>'
        token_summary_rows += f'''<tr>
            <td class="token-name">{t}</td>
            <td class="num buy">{tt['buy_eth']:.4f}</td>
            <td class="num">{tt['buys']}</td>
            <td class="num sell">{tt['sell_eth']:.4f}{extra}</td>
            <td class="num">{tt['sells']}</td>
        </tr>'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DGMD Wallet Activity Report</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0a0e14;
    color: #c9d1d9;
    padding: 24px;
    max-width: 1100px;
    margin: 0 auto;
    line-height: 1.5;
}}

/* Header */
.header {{ margin-bottom: 28px; }}
h1 {{
    color: #fff;
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 4px;
    letter-spacing: -0.5px;
}}
.subtitle {{ color: #6e7681; font-size: 13px; }}

/* Top summary cards */
.cards {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 36px;
}}
.card {{
    background: #111820;
    border: 1px solid #1c2432;
    border-radius: 12px;
    padding: 18px;
    position: relative;
    overflow: hidden;
}}
.card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}}
.card.card-in::before {{ background: #3fb950; }}
.card.card-out::before {{ background: #f85149; }}
.card.card-net::before {{ background: #58a6ff; }}
.card.card-usdg::before {{ background: #d2a8ff; }}
.card .label {{
    color: #6e7681;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600;
}}
.card .value {{
    font-size: 28px;
    font-weight: 700;
    margin-top: 6px;
    letter-spacing: -0.5px;
}}
.card .sub {{ color: #484f58; font-size: 11px; margin-top: 4px; }}

/* Colors */
.eth {{ color: #58a6ff; }}
.sell {{ color: #f85149; }}
.buy {{ color: #3fb950; }}
.usdg {{ color: #d2a8ff; font-size: 12px; }}
.dim {{ color: #484f58; }}

/* Wallet sections */
.wallet-section {{
    background: #111820;
    border: 1px solid #1c2432;
    border-radius: 12px;
    padding: 0;
    margin-bottom: 16px;
    overflow: hidden;
}}
.wallet-top {{
    padding: 18px 22px 14px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 12px;
}}
.wallet-header {{
    display: flex;
    align-items: baseline;
    gap: 10px;
}}
.wallet-header h2 {{
    color: #fff;
    font-size: 18px;
    font-weight: 700;
}}
.wallet-addr {{
    color: #3d4450;
    font-size: 10px;
    font-family: 'SF Mono', 'Fira Code', monospace;
    background: #0a0e14;
    padding: 3px 8px;
    border-radius: 4px;
    border: 1px solid #1c2432;
}}

.wallet-cards {{
    display: flex;
    gap: 10px;
}}
.mini-card {{
    background: #0a0e14;
    border: 1px solid #1c2432;
    border-radius: 8px;
    padding: 8px 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 110px;
}}
.mini-label {{
    color: #6e7681;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
}}
.mini-value {{
    font-size: 17px;
    font-weight: 700;
    margin-top: 2px;
    letter-spacing: -0.3px;
}}

/* Tables */
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}
thead {{ background: #0d1219; }}
th {{
    text-align: left;
    color: #484f58;
    font-weight: 600;
    padding: 10px 16px;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    border-bottom: 1px solid #1c2432;
}}
td {{
    padding: 10px 16px;
    border-bottom: 1px solid #141c27;
}}
tbody tr:hover {{ background: #0d1219; }}
.num {{
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 13px;
}}
.token-name {{
    font-weight: 600;
    color: #e6edf3;
    font-size: 13px;
}}
.total-row {{
    font-weight: 700;
    background: #0d1219;
}}
.total-row td {{
    padding-top: 12px;
    padding-bottom: 12px;
    border-top: 2px solid #1c2432;
    border-bottom: none;
}}

/* Notes */
.note {{
    background: #0d1219;
    border-left: 3px solid #d29922;
    padding: 10px 16px;
    font-size: 12px;
    color: #6e7681;
    margin: 0;
    border-radius: 0;
}}
.note strong {{ color: #d29922; }}

/* Grand total */
.grand-total {{
    background: #111820;
    border: 2px solid #1c2432;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 24px;
}}
.grand-total-header {{
    padding: 18px 22px 0;
}}
.grand-total h2 {{
    color: #58a6ff;
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 14px;
}}

/* Footer */
.footer {{
    font-size: 11px;
    color: #3d4450;
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid #1c2432;
}}
.footer code {{
    background: #111820;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    color: #484f58;
    border: 1px solid #1c2432;
}}

@media (max-width: 768px) {{
    .cards {{ grid-template-columns: 1fr 1fr; gap: 10px; }}
    .wallet-top {{ flex-direction: column; }}
    .wallet-cards {{ flex-wrap: wrap; }}
    .wallet-header {{ flex-direction: column; gap: 4px; }}
    body {{ padding: 14px; }}
}}
@media (max-width: 480px) {{
    .cards {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<div class="header">
    <h1>DGMD Wallet Activity Report</h1>
    <p class="subtitle">All-time activity across 5 tracked wallets &mdash; VIBESTR, GVC, MOODS, STOKED + OTC</p>
</div>

<div class="cards">
    <div class="card card-in">
        <div class="label">Total ETH In</div>
        <div class="value buy">{grand_in:.2f} ETH</div>
        <div class="sub">All buys (VIBESTR + GVC)</div>
    </div>
    <div class="card card-out">
        <div class="label">Total ETH Out</div>
        <div class="value sell">{grand_out:.2f} ETH</div>
        <div class="sub">All sells + OTC</div>
    </div>
    <div class="card card-net">
        <div class="label">Net Flow</div>
        <div class="value {'sell' if net > 0 else 'buy'}">{net:+.2f} ETH</div>
        <div class="sub">{'More out than in' if net > 0 else 'More in than out'}</div>
    </div>
    <div class="card card-usdg">
        <div class="label">USDG Received</div>
        <div class="value usdg" style="font-size:22px">${grand_usdg:.2f}</div>
        <div class="sub">STOKED &rarr; USDG sells</div>
    </div>
</div>

<!-- Per-wallet sections -->
{wallet_sections}

<!-- OTC Sales -->
<div class="wallet-section">
    <div class="wallet-top">
        <div class="wallet-header">
            <h2>OTC (Off-Chain) Sales</h2>
        </div>
        <div class="wallet-cards">
            <div class="mini-card">
                <span class="mini-label">ETH Out</span>
                <span class="mini-value sell">{OTC_ETH:.1f}</span>
            </div>
        </div>
    </div>
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
                <td class="token-name">{s['token']}</td>
                <td>{s['buyer']}</td>
                <td class="num">{s['amount']}</td>
                <td class="num">{s['price']:.1f}</td>
                <td class="num sell">{s['total']:.1f}</td>
            </tr>""" for s in OTC_SALES)}
            <tr class="total-row">
                <td colspan="4">TOTAL</td>
                <td class="num sell">{OTC_ETH:.1f}</td>
            </tr>
        </tbody>
    </table>
    <div class="note">
        <strong>Note:</strong> 50 VIBESTR sold off-chain at 0.2 ETH each = 10 ETH total.
    </div>
</div>

<!-- Grand Total -->
<div class="grand-total">
    <div class="grand-total-header">
        <h2>Grand Total &mdash; All Tokens</h2>
    </div>
    <table>
        <thead>
            <tr>
                <th>Token</th>
                <th class="num">ETH In (Buys)</th>
                <th class="num"># Buys</th>
                <th class="num">ETH Out (Sells)</th>
                <th class="num"># Sells</th>
            </tr>
        </thead>
        <tbody>
            {token_summary_rows}
            <tr>
                <td class="token-name">OTC</td>
                <td class="num buy">0.0000</td>
                <td class="num">0</td>
                <td class="num sell">{OTC_ETH:.4f}</td>
                <td class="num">{len(OTC_SALES)}</td>
            </tr>
            <tr class="total-row">
                <td style="font-size:15px">GRAND TOTAL</td>
                <td class="num buy" style="font-size:15px">{grand_in:.4f} ETH</td>
                <td></td>
                <td class="num sell" style="font-size:15px">{grand_out:.4f} ETH</td>
                <td></td>
            </tr>
        </tbody>
    </table>
    <div class="note" style="margin-top:14px">
        <strong>Token flow:</strong> ETH &rarr; buy GVC &amp; VIBESTR &rarr; Cryo Chamber (1 GVC = 3 MOODS) &rarr; some MOODS sold directly, most MOODS &rarr; ANVIL &rarr; STOKED &rarr; sold for ETH/USDG. No ETH was spent buying STOKED or MOODS directly.
    </div>
</div>

<div class="footer">
    <strong>Tracked Wallets:</strong><br>
    {'<br>'.join(f"{wn}: <code>{addr}</code>" for wn, addr in WALLET_ADDRS.items())}
    <br><br>
    <strong>Data Sources:</strong> Etherscan V2 API (VIBESTR, GVC on Ethereum), Robinhood Chain Blockscout (STOKED), OpenSea (MOODS), Manual (OTC)
</div>

</body>
</html>'''

    os.makedirs('public', exist_ok=True)
    with open('public/index.html', 'w') as f:
        f.write(html)
    print('Report saved to public/index.html')


if __name__ == '__main__':
    build_report()
