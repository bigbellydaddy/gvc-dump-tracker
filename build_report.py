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
WALLET_SHORT = {
    'IKZ1': 'IKZ1',
    'DGMD22': 'DGMD22',
    'EraOfVibes': 'EraOfVibes',
    'Extra25': 'Extra25',
    'InvestmentFund1': 'InvFund1',
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


def fmt_amt(a):
    if a >= 1e6:
        return f'{a/1e6:.1f}M'
    elif a >= 1e3:
        return f'{a/1e3:.0f}K'
    return f'{a:.0f}'


def build_report():
    vibestr_gvc, stoked, moods = load_data()

    # Per-wallet data
    wallet_data = {}
    for wn in WALLETS:
        addr = WALLET_ADDRS[wn]
        short = WALLET_SHORT[wn]
        addr_short = addr[:6] + '...' + addr[-4:]

        # STOKED individual sells
        sd = [r for r in stoked if r.get('wallet_name') == wn]
        stoked_eth_sells = [r for r in sd if r['value_eth'] > 0]
        stoked_usdg_sells = [r for r in sd if r['value_eth'] == 0 and r.get('value_usd', 0) > 0]
        stoked_eth_total = sum(r['value_eth'] for r in stoked_eth_sells)
        stoked_usdg_total = sum(r.get('value_usd', 0) for r in stoked_usdg_sells)
        stoked_amt_total = sum(r['amount'] for r in stoked_eth_sells + stoked_usdg_sells)

        # VIBESTR individual buys and sells
        vd = [r for r in vibestr_gvc if r['token'] == 'VIBESTR' and r.get('wallet_name') == wn]
        vib_buys = sorted([r for r in vd if r['type'] == 'buy' and r['value_eth'] > 0], key=lambda x: x['value_eth'], reverse=True)
        vib_sells = sorted([r for r in vd if r['type'] == 'sell' and r['value_eth'] > 0], key=lambda x: x['value_eth'], reverse=True)
        vib_buy_eth = sum(r['value_eth'] for r in vib_buys)
        vib_sell_eth = sum(r['value_eth'] for r in vib_sells)
        vib_buy_amt = sum(r['amount'] for r in vib_buys)
        vib_sell_amt = sum(r['amount'] for r in vib_sells)

        # GVC totals only
        gd = [r for r in vibestr_gvc if r['token'] == 'GVC' and r.get('wallet_name') == wn]
        gvc_buys = [r for r in gd if r['type'] == 'buy' and r['value_eth'] > 0]
        gvc_sells = [r for r in gd if r['type'] == 'sell' and r['value_eth'] > 0]
        gvc_buy_eth = sum(r['value_eth'] for r in gvc_buys)
        gvc_sell_eth = sum(r['value_eth'] for r in gvc_sells)
        gvc_nfts_bought = len(gvc_buys)
        gvc_nfts_sold = sum(int(r['amount']) for r in gvc_sells)

        # MOODS totals only
        md = [r for r in moods if r.get('wallet_name') == wn and r['type'] == 'sell']
        moods_sell_eth = sum(r['value_eth'] for r in md)
        moods_count = len(md)

        # Wallet total
        w_in = vib_buy_eth + gvc_buy_eth
        w_out = vib_sell_eth + gvc_sell_eth + stoked_eth_total + moods_sell_eth

        wallet_data[wn] = {
            'addr': addr, 'addr_short': addr_short, 'short': short,
            'stoked_eth_sells': stoked_eth_sells, 'stoked_usdg_sells': stoked_usdg_sells,
            'stoked_eth_total': stoked_eth_total, 'stoked_usdg_total': stoked_usdg_total,
            'stoked_amt_total': stoked_amt_total,
            'vib_buys': vib_buys, 'vib_sells': vib_sells,
            'vib_buy_eth': vib_buy_eth, 'vib_sell_eth': vib_sell_eth,
            'vib_buy_amt': vib_buy_amt, 'vib_sell_amt': vib_sell_amt,
            'gvc_buy_eth': gvc_buy_eth, 'gvc_sell_eth': gvc_sell_eth,
            'gvc_nfts_bought': gvc_nfts_bought, 'gvc_nfts_sold': gvc_nfts_sold,
            'moods_sell_eth': moods_sell_eth, 'moods_count': moods_count,
            'w_in': w_in, 'w_out': w_out,
        }

    # Grand totals
    total_stoked_eth = sum(w['stoked_eth_total'] for w in wallet_data.values())
    total_stoked_usdg = sum(w['stoked_usdg_total'] for w in wallet_data.values())
    total_stoked_sells = sum(len(w['stoked_eth_sells']) + len(w['stoked_usdg_sells']) for w in wallet_data.values())
    total_vib_buy_eth = sum(w['vib_buy_eth'] for w in wallet_data.values())
    total_vib_sell_eth = sum(w['vib_sell_eth'] for w in wallet_data.values())
    total_vib_buys = sum(len(w['vib_buys']) for w in wallet_data.values())
    total_vib_sells = sum(len(w['vib_sells']) for w in wallet_data.values())
    total_vib_sell_amt = sum(w['vib_sell_amt'] for w in wallet_data.values())
    total_gvc_buy_eth = sum(w['gvc_buy_eth'] for w in wallet_data.values())
    total_gvc_sell_eth = sum(w['gvc_sell_eth'] for w in wallet_data.values())
    total_gvc_bought = sum(w['gvc_nfts_bought'] for w in wallet_data.values())
    total_gvc_sold = sum(w['gvc_nfts_sold'] for w in wallet_data.values())
    total_moods_eth = sum(w['moods_sell_eth'] for w in wallet_data.values())
    total_moods_count = sum(w['moods_count'] for w in wallet_data.values())

    grand_in = total_vib_buy_eth + total_gvc_buy_eth
    grand_out = total_vib_sell_eth + total_gvc_sell_eth + total_stoked_eth + total_moods_eth + OTC_ETH
    grand_net = grand_out - grand_in

    # Build wallet columns
    columns_html = ''
    for wn in WALLETS:
        w = wallet_data[wn]
        w_total = w['stoked_eth_total'] + w['vib_sell_eth'] + w['gvc_sell_eth'] + w['moods_sell_eth']
        w_net = w['w_out'] - w['w_in']

        # STOKED rows
        stoked_rows = ''
        if w['stoked_eth_sells'] or w['stoked_usdg_sells']:
            for r in w['stoked_eth_sells']:
                stoked_rows += f'<tr><td>{fmt_amt(r["amount"])}</td><td class="num">{r["value_eth"]:.2f}</td></tr>\n'
            for r in w['stoked_usdg_sells']:
                stoked_rows += f'<tr><td>{fmt_amt(r["amount"])}</td><td class="num usdg">${r["value_usd"]:.2f}</td></tr>\n'
            usdg_sub = f' <span class="usdg">+ ${w["stoked_usdg_total"]:.2f}</span>' if w['stoked_usdg_total'] > 0 else ''
            stoked_section = f'''
            <div class="token-section">
                <div class="token-header">STOKED</div>
                <table><tbody>{stoked_rows}</tbody></table>
                <div class="sub-total">Sub: {fmt_amt(w["stoked_amt_total"])} &middot; <span class="sell">{w["stoked_eth_total"]:.2f} ETH</span>{usdg_sub}</div>
            </div>'''
        else:
            stoked_section = '''
            <div class="token-section">
                <div class="token-header">STOKED</div>
                <div class="no-sells">no sells</div>
            </div>'''

        # VIBESTR section
        vib_buy_rows = ''
        for r in w['vib_buys']:
            vib_buy_rows += f'<tr><td>{fmt_amt(r["amount"])}</td><td class="num buy">{r["value_eth"]:.2f}</td></tr>\n'
        vib_sell_rows = ''
        for r in w['vib_sells']:
            vib_sell_rows += f'<tr><td>{fmt_amt(r["amount"])}</td><td class="num sell">{r["value_eth"]:.2f}</td></tr>\n'

        if w['vib_buys'] or w['vib_sells']:
            vib_net = w['vib_sell_eth'] - w['vib_buy_eth']
            vib_net_class = 'sell' if vib_net > 0 else 'buy'
            buys_block = ''
            if w['vib_buys']:
                buys_block = f'''<div class="tx-group">
                    <div class="tx-label">Buys ({len(w["vib_buys"])})</div>
                    <table><tbody>{vib_buy_rows}</tbody></table>
                </div>'''
            sells_block = ''
            if w['vib_sells']:
                sells_block = f'''<div class="tx-group">
                    <div class="tx-label">Sells ({len(w["vib_sells"])})</div>
                    <table><tbody>{vib_sell_rows}</tbody></table>
                </div>'''
            vibestr_section = f'''
            <div class="token-section">
                <div class="token-header">VIBESTR</div>
                {buys_block}
                {sells_block}
                <div class="sub-total">In: <span class="buy">{w["vib_buy_eth"]:.2f}</span> &middot; Out: <span class="sell">{w["vib_sell_eth"]:.2f}</span> &middot; Net: <span class="{vib_net_class}">{vib_net:+.2f}</span></div>
            </div>'''
        else:
            vibestr_section = '''
            <div class="token-section">
                <div class="token-header">VIBESTR</div>
                <div class="no-sells">no activity</div>
            </div>'''

        # GVC summary
        if w['gvc_buy_eth'] > 0 or w['gvc_sell_eth'] > 0:
            gvc_net = w['gvc_sell_eth'] - w['gvc_buy_eth']
            gvc_net_class = 'sell' if gvc_net > 0 else 'buy'
            gvc_section = f'''
            <div class="token-section">
                <div class="token-header">GVC <span class="badge">NFT</span></div>
                <div class="summary-line">Bought: {w["gvc_nfts_bought"]} NFTs &middot; <span class="buy">{w["gvc_buy_eth"]:.2f} ETH</span></div>
                <div class="summary-line">Sold: {w["gvc_nfts_sold"]} NFTs &middot; <span class="sell">{w["gvc_sell_eth"]:.2f} ETH</span></div>
                <div class="sub-total">Net: <span class="{gvc_net_class}">{gvc_net:+.2f} ETH</span></div>
            </div>'''
        else:
            gvc_section = '''
            <div class="token-section">
                <div class="token-header">GVC <span class="badge">NFT</span></div>
                <div class="no-sells">no activity</div>
            </div>'''

        # MOODS summary
        if w['moods_sell_eth'] > 0:
            moods_section = f'''
            <div class="token-section">
                <div class="token-header">MOODS <span class="badge">NFT</span></div>
                <div class="summary-line">Sold: {w["moods_count"]} NFTs &middot; <span class="sell">{w["moods_sell_eth"]:.4f} ETH</span></div>
            </div>'''
        else:
            moods_section = ''

        columns_html += f'''
        <div class="wallet-col">
            <div class="col-header">
                <div class="col-name">{w["short"]}</div>
                <div class="col-addr">({w["addr_short"]})</div>
                <div class="col-total"><span class="sell">{w_total:.2f} ETH</span> out</div>
            </div>
            {stoked_section}
            {vibestr_section}
            {gvc_section}
            {moods_section}
            <div class="wallet-total-bar">
                <span>ETH In: <span class="buy">{w["w_in"]:.2f}</span></span>
                <span>ETH Out: <span class="sell">{w["w_out"]:.2f}</span></span>
                <span>Net: <span class="{'sell' if w_net > 0 else 'buy'}">{w_net:+.2f}</span></span>
            </div>
        </div>'''

    # Summary cards
    vib_net = total_vib_sell_eth - total_vib_buy_eth + OTC_ETH
    gvc_net = total_gvc_sell_eth - total_gvc_buy_eth

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
    padding: 20px;
    line-height: 1.4;
}}
h1 {{
    color: #fff;
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 4px;
    letter-spacing: -0.5px;
}}
.subtitle {{ color: #6e7681; font-size: 12px; margin-bottom: 20px; }}

.sell {{ color: #f85149; }}
.buy {{ color: #3fb950; }}
.usdg {{ color: #d2a8ff; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; font-family: 'SF Mono', 'Fira Code', monospace; }}

/* Wallet columns */
.columns {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin-bottom: 24px;
    overflow-x: auto;
}}
.wallet-col {{
    background: #111820;
    border: 1px solid #1c2432;
    border-radius: 10px;
    overflow: hidden;
    min-width: 200px;
}}
.col-header {{
    padding: 14px 12px 10px;
    border-bottom: 2px solid #1c2432;
}}
.col-name {{
    color: #fff;
    font-size: 15px;
    font-weight: 700;
}}
.col-addr {{
    color: #3d4450;
    font-size: 9px;
    font-family: 'SF Mono', monospace;
    margin-top: 2px;
}}
.col-total {{
    font-size: 20px;
    font-weight: 700;
    margin-top: 6px;
    font-family: 'SF Mono', monospace;
}}

/* Token sections */
.token-section {{
    padding: 10px 12px;
    border-bottom: 1px solid #1c2432;
}}
.token-header {{
    color: #58a6ff;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
}}
.token-header .badge {{
    background: #1c2432;
    color: #6e7681;
    font-size: 9px;
    padding: 1px 5px;
    border-radius: 3px;
    letter-spacing: 0;
    text-transform: uppercase;
    vertical-align: middle;
}}
.token-section table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}}
.token-section td {{
    padding: 2px 0;
    font-family: 'SF Mono', monospace;
    font-size: 12px;
}}
.token-section td:first-child {{
    color: #8b949e;
}}
.token-section td:last-child {{
    text-align: right;
    font-weight: 600;
}}
.tx-group {{ margin-bottom: 4px; }}
.tx-label {{
    color: #6e7681;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
    margin-top: 4px;
}}
.sub-total {{
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid #1c2432;
    font-size: 11px;
    font-weight: 700;
    font-family: 'SF Mono', monospace;
}}
.summary-line {{
    font-size: 12px;
    font-family: 'SF Mono', monospace;
    padding: 2px 0;
}}
.no-sells {{
    color: #3d4450;
    font-size: 11px;
    font-style: italic;
    padding: 4px 0;
}}

.wallet-total-bar {{
    padding: 10px 12px;
    background: #0d1219;
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 11px;
    font-weight: 700;
    font-family: 'SF Mono', monospace;
}}

/* Summary cards at bottom */
.summary-cards {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}}
.summary-card {{
    background: #111820;
    border: 1px solid #1c2432;
    border-radius: 10px;
    padding: 16px;
    overflow: hidden;
    position: relative;
}}
.summary-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}}
.summary-card.sc-stoked::before {{ background: #f0883e; }}
.summary-card.sc-vibestr::before {{ background: #3fb950; }}
.summary-card.sc-gvc::before {{ background: #58a6ff; }}
.summary-card.sc-grand::before {{ background: linear-gradient(90deg, #3fb950, #f85149); }}
.sc-title {{
    font-size: 12px;
    font-weight: 700;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}}
.sc-subtitle {{
    font-size: 10px;
    color: #484f58;
    margin-bottom: 8px;
}}
.sc-big {{
    font-size: 28px;
    font-weight: 800;
    font-family: 'SF Mono', monospace;
    letter-spacing: -1px;
}}
.sc-detail {{
    font-size: 11px;
    color: #6e7681;
    margin-top: 4px;
    font-family: 'SF Mono', monospace;
}}

/* OTC section */
.otc-section {{
    background: #111820;
    border: 1px solid #1c2432;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 20px;
}}
.otc-section h3 {{
    color: #d2a8ff;
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}}
.otc-section table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    max-width: 500px;
}}
.otc-section th {{
    text-align: left;
    color: #484f58;
    font-weight: 600;
    padding: 4px 8px;
    font-size: 10px;
    text-transform: uppercase;
}}
.otc-section td {{
    padding: 4px 8px;
    font-family: 'SF Mono', monospace;
}}

/* Token flow note */
.flow-note {{
    background: #0d1219;
    border-left: 3px solid #d29922;
    padding: 10px 16px;
    font-size: 12px;
    color: #6e7681;
    border-radius: 0 8px 8px 0;
    margin-bottom: 20px;
}}
.flow-note strong {{ color: #d29922; }}

/* Footer */
.footer {{
    font-size: 10px;
    color: #3d4450;
    margin-top: 24px;
    padding-top: 12px;
    border-top: 1px solid #1c2432;
}}
.footer code {{
    background: #111820;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 9px;
    color: #484f58;
}}

@media (max-width: 1100px) {{
    .columns {{ grid-template-columns: repeat(3, 1fr); }}
    .summary-cards {{ grid-template-columns: repeat(2, 1fr); }}
}}
@media (max-width: 700px) {{
    .columns {{ grid-template-columns: 1fr 1fr; }}
    .summary-cards {{ grid-template-columns: 1fr; }}
    body {{ padding: 12px; }}
}}
@media (max-width: 450px) {{
    .columns {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<h1>DGMD STOKED + VIBESTR + GVC: All Sells</h1>
<p class="subtitle">All-time activity across 5 tracked wallets. STOKED &amp; VIBESTR individual transactions shown. GVC &amp; MOODS totals only.</p>

<div class="columns">
{columns_html}
</div>

<!-- OTC Sales -->
<div class="otc-section">
    <h3>OTC (Off-Chain) Sales</h3>
    <table>
        <thead><tr><th>Token</th><th>Buyer</th><th>Amount</th><th>Price</th><th>Total</th></tr></thead>
        <tbody>
            {''.join(f'<tr><td>{s["token"]}</td><td>{s["buyer"]}</td><td class="num">{s["amount"]}</td><td class="num">{s["price"]}</td><td class="num sell">{s["total"]:.1f} ETH</td></tr>' for s in OTC_SALES)}
        </tbody>
    </table>
    <div style="font-size:11px; color:#6e7681; margin-top:6px;">50 VIBESTR sold off-chain at 0.2 ETH each = <span class="sell">10 ETH</span></div>
</div>

<!-- Summary cards -->
<div class="summary-cards">
    <div class="summary-card sc-stoked">
        <div class="sc-title">STOKED Total ({total_stoked_sells} sells)</div>
        <div class="sc-subtitle">Cryo &rarr; STOKED &rarr; sold for ETH/USDG</div>
        <div class="sc-big sell">{total_stoked_eth:.2f} ETH</div>
        <div class="sc-detail usdg">+ ${total_stoked_usdg:.2f} USDG</div>
    </div>
    <div class="summary-card sc-vibestr">
        <div class="sc-title">VIBESTR Total</div>
        <div class="sc-subtitle">{fmt_amt(total_vib_sell_amt)} sold on-chain + 50 OTC</div>
        <div class="sc-big">
            <span class="buy">{total_vib_buy_eth:.2f}</span> in /
            <span class="sell">{total_vib_sell_eth + OTC_ETH:.2f}</span> out
        </div>
        <div class="sc-detail">Net: <span class="{'sell' if vib_net > 0 else 'buy'}">{vib_net:+.2f} ETH</span> (incl OTC)</div>
    </div>
    <div class="summary-card sc-gvc">
        <div class="sc-title">GVC Sold Directly ({total_gvc_sold} sales)</div>
        <div class="sc-subtitle">{total_gvc_bought} bought &middot; {total_gvc_sold} sold on OpenSea/on-chain</div>
        <div class="sc-big">
            <span class="buy">{total_gvc_buy_eth:.2f}</span> in /
            <span class="sell">{total_gvc_sell_eth:.2f}</span> out
        </div>
        <div class="sc-detail">Net: <span class="{'sell' if gvc_net > 0 else 'buy'}">{gvc_net:+.2f} ETH</span></div>
    </div>
    <div class="summary-card sc-grand">
        <div class="sc-title">Grand Total (all in ETH)</div>
        <div class="sc-subtitle">STOKED + VIBESTR + GVC + MOODS + OTC</div>
        <div class="sc-big sell">{grand_out:.2f} ETH</div>
        <div class="sc-detail">In: <span class="buy">{grand_in:.2f}</span> &middot; Out: <span class="sell">{grand_out:.2f}</span> &middot; Net: <span class="{'sell' if grand_net > 0 else 'buy'}">{grand_net:+.2f}</span></div>
        <div class="sc-detail usdg">+ ${total_stoked_usdg:.2f} USDG from STOKED</div>
    </div>
</div>

{f'<div class="summary-cards" style="grid-template-columns:1fr"><div class="summary-card" style="border-color:#3d4450"><div class="sc-title">MOODS ({total_moods_count} sales)</div><div class="sc-subtitle">Sold on OpenSea (Robinhood chain)</div><div class="sc-big sell">{total_moods_eth:.4f} ETH</div></div></div>' if total_moods_count > 0 else ''}

<div class="flow-note">
    <strong>Token flow:</strong> ETH &rarr; buy GVC &amp; VIBESTR &rarr; Cryo Chamber (1 GVC = 3 MOODS) &rarr; some MOODS sold directly, most MOODS &rarr; ANVIL &rarr; STOKED &rarr; sold for ETH/USDG. No ETH was spent buying STOKED or MOODS directly.
</div>

<div class="footer">
    <strong>Tracked Wallets:</strong><br>
    {'<br>'.join(f"{wn}: <code>{addr}</code>" for wn, addr in WALLET_ADDRS.items())}
    <br><br>
    <strong>Data Sources:</strong> Etherscan V2 API (VIBESTR, GVC on Ethereum), Robinhood Chain (STOKED), OpenSea (MOODS), Manual (OTC)
</div>

</body>
</html>'''

    os.makedirs('public', exist_ok=True)
    with open('public/index.html', 'w') as f:
        f.write(html)
    print('Report saved to public/index.html')


if __name__ == '__main__':
    build_report()
