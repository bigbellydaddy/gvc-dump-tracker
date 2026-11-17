#!/usr/bin/env python3
"""Fast fetch using Etherscan V2 API for all 5 wallets."""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from collections import defaultdict
import os

API_KEY = 'KI3JG1UGI7B7SNZIVZK943XRV8SFK83NHG'
BASE = 'https://api.etherscan.io/v2/api?chainid=1'

WALLETS = {
    '0xb206a73f101071f7a5027275ef52f827b2ea2b11': 'IKZ1',
    '0x2d13c884c4c418664abb1b4a7f491dd89247e42e': 'DGMD22',
    '0x662307a93bce119539a81408186bba28f01613cf': 'EraOfVibes',
    '0x83e574af1bf5813f8552d434b213548e6bd4f35d': 'Extra25',
    '0xa1862a515fe0d692392fd1e51d7aeab674a6864b': 'InvestmentFund1'
}

VAULT = '0x8972e0a32d509708c55e5a46d05966e690a454ca'
CRYO_CHAMBER = '0xae2ddc0ae9c498c82c01e34d48a7e84165322f26'

ALL_WALLETS = set(w.lower() for w in WALLETS.keys())
SKIP_DESTINATIONS = ALL_WALLETS | {VAULT.lower(), CRYO_CHAMBER.lower()}

VIBESTR = '0xd0cc2b0efb168bfe1f94a948d8df70fa10257196'
GVC = '0xb8ea78fcacef50d41375e44e6814ebba36bb33c4'
WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'

LAST_REQ = 0
REQ_COUNT = 0


def api(params, retries=3):
    global LAST_REQ, REQ_COUNT
    # Rate limit: 5 calls/sec
    elapsed = time.time() - LAST_REQ
    if elapsed < 0.25:
        time.sleep(0.25 - elapsed)

    url = f'{BASE}&{params}&apikey={API_KEY}'
    for attempt in range(retries):
        try:
            REQ_COUNT += 1
            LAST_REQ = time.time()
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            if data.get('status') == '1':
                return data.get('result', [])
            msg = data.get('result', '')
            if 'Max rate limit' in str(msg):
                time.sleep(1)
                continue
            return []
        except Exception as e:
            print(f'    Error: {e}, retry {attempt+1}', flush=True)
            time.sleep(1)
    return []


def fetch_all_pages(params_base, max_results=10000):
    all_items = []
    page = 1
    while len(all_items) < max_results:
        items = api(f'{params_base}&page={page}&offset=1000&sort=asc')
        if not items:
            break
        all_items.extend(items)
        if len(items) < 1000:
            break
        page += 1
    return all_items


def process_wallet(wallet_addr, wallet_name):
    wallet_lower = wallet_addr.lower()
    results = []

    # 1. Get VIBESTR ERC-20 transfers
    print(f'  Fetching VIBESTR transfers...', flush=True)
    vibestr_txs = fetch_all_pages(
        f'module=account&action=tokentx&address={wallet_addr}&contractaddress={VIBESTR}'
    )
    print(f'    Got {len(vibestr_txs)} VIBESTR transfers', flush=True)

    # 2. Get GVC ERC-721 transfers
    print(f'  Fetching GVC NFT transfers...', flush=True)
    gvc_txs = fetch_all_pages(
        f'module=account&action=tokennfttx&address={wallet_addr}&contractaddress={GVC}'
    )
    print(f'    Got {len(gvc_txs)} GVC transfers', flush=True)

    # 3. Get internal transactions (for ETH from Uniswap swaps)
    print(f'  Fetching internal transactions...', flush=True)
    internal_txs = fetch_all_pages(
        f'module=account&action=txlistinternal&address={wallet_addr}'
    )
    print(f'    Got {len(internal_txs)} internal txs', flush=True)

    # 4. Get normal transactions (for tx values - NFT sales)
    print(f'  Fetching normal transactions...', flush=True)
    normal_txs = fetch_all_pages(
        f'module=account&action=txlist&address={wallet_addr}'
    )
    print(f'    Got {len(normal_txs)} normal txs', flush=True)

    # 5. Get ERC-20 transfers for WETH specifically (for WETH in swaps)
    print(f'  Fetching WETH transfers...', flush=True)
    weth_txs = fetch_all_pages(
        f'module=account&action=tokentx&address={wallet_addr}&contractaddress={WETH}'
    )
    print(f'    Got {len(weth_txs)} WETH transfers', flush=True)

    # Build lookup maps
    # Internal tx: tx_hash -> max ETH received by wallet
    internal_eth = defaultdict(float)
    for itx in internal_txs:
        h = itx.get('hash', '')
        to_addr = itx.get('to', '').lower()
        from_addr = itx.get('from', '').lower()
        val = int(itx.get('value', '0')) / 1e18
        if val < 0.0001:
            continue
        if to_addr == wallet_lower:
            internal_eth[h] = max(internal_eth[h], val)

    # Normal tx: tx_hash -> value
    normal_val = {}
    for tx in normal_txs:
        h = tx.get('hash', '')
        val = int(tx.get('value', '0')) / 1e18
        normal_val[h] = val

    # WETH: tx_hash -> total WETH received/sent (sum all transfers in same tx)
    weth_received = defaultdict(float)
    weth_sent = defaultdict(float)
    for wtx in weth_txs:
        h = wtx.get('hash', '')
        to_addr = wtx.get('to', '').lower()
        from_addr = wtx.get('from', '').lower()
        val = int(wtx.get('value', '0')) / 1e18
        if val < 0.0001:
            continue
        if to_addr == wallet_lower:
            weth_received[h] += val
        if from_addr == wallet_lower:
            weth_sent[h] += val

    # Process VIBESTR transfers
    for tx in vibestr_txs:
        from_addr = tx.get('from', '').lower()
        to_addr = tx.get('to', '').lower()
        h = tx.get('hash', '')

        if from_addr in ALL_WALLETS and to_addr in ALL_WALLETS:
            continue

        is_sell = from_addr == wallet_lower
        is_buy = to_addr == wallet_lower
        if not is_sell and not is_buy:
            continue

        dec = int(tx.get('tokenDecimal', '18'))
        amount = int(tx.get('value', '0')) / (10 ** dec)
        if amount == 0:
            continue

        # Find ETH value
        value_eth = 0
        if is_sell:
            value_eth = internal_eth.get(h, 0)
            if value_eth < 0.001:
                value_eth = weth_received.get(h, 0)
        else:
            value_eth = normal_val.get(h, 0)
            if value_eth < 0.001:
                value_eth = weth_sent.get(h, 0)
            if value_eth < 0.001:
                # Check internal txs where wallet sends
                for itx in internal_txs:
                    if itx.get('hash', '') == h:
                        fr = itx.get('from', '').lower()
                        v = int(itx.get('value', '0')) / 1e18
                        if fr == wallet_lower and v > value_eth:
                            value_eth = v

        ts = int(tx.get('timeStamp', '0'))
        date_str = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else 'unknown'

        results.append({
            'date': date_str,
            'type': 'sell' if is_sell else 'buy',
            'amount': amount,
            'value_eth': value_eth,
            'tx_hash': h,
            'wallet': wallet_addr,
            'wallet_name': wallet_name,
            'token': 'VIBESTR'
        })

    # Process GVC NFT transfers
    # Group by tx hash for batch sales
    gvc_by_tx = defaultdict(list)
    for tx in gvc_txs:
        gvc_by_tx[tx.get('hash', '')].append(tx)

    for h, txs_in_hash in gvc_by_tx.items():
        for tx in txs_in_hash:
            from_addr = tx.get('from', '').lower()
            to_addr = tx.get('to', '').lower()

            if from_addr in ALL_WALLETS and to_addr in ALL_WALLETS:
                continue

            is_sell = from_addr == wallet_lower
            is_buy = to_addr == wallet_lower
            if not is_sell and not is_buy:
                continue

            # Skip transfers to/from vault or Cryo Chamber (internal moves, not market trades)
            if is_sell and to_addr in SKIP_DESTINATIONS:
                continue
            if is_buy and from_addr in SKIP_DESTINATIONS:
                continue

            # Find ETH value for this NFT tx
            value_eth = 0
            if is_sell:
                value_eth = normal_val.get(h, 0)
                if value_eth < 0.001:
                    value_eth = internal_eth.get(h, 0)
                if value_eth < 0.001:
                    value_eth = weth_received.get(h, 0)
            else:
                value_eth = normal_val.get(h, 0)
                if value_eth < 0.001:
                    value_eth = weth_sent.get(h, 0)
                if value_eth < 0.001:
                    for itx in internal_txs:
                        if itx.get('hash', '') == h:
                            fr = itx.get('from', '').lower()
                            v = int(itx.get('value', '0')) / 1e18
                            if fr == wallet_lower and v > value_eth:
                                value_eth = v

            # Divide by NFTs in same direction in same tx
            same_dir = [t for t in txs_in_hash
                       if (t.get('from', '').lower() == wallet_lower) == is_sell]
            if len(same_dir) > 1 and value_eth > 0:
                value_eth = value_eth / len(same_dir)

            ts = int(tx.get('timeStamp', '0'))
            date_str = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else 'unknown'

            results.append({
                'date': date_str,
                'type': 'sell' if is_sell else 'buy',
                'amount': 1,
                'value_eth': value_eth,
                'tx_hash': h,
                'wallet': wallet_addr,
                'wallet_name': wallet_name,
                'token': 'GVC'
            })

    # Print summary
    for tn in ['VIBESTR', 'GVC']:
        td = [r for r in results if r['token'] == tn]
        sells = [r for r in td if r['type'] == 'sell']
        buys = [r for r in td if r['type'] == 'buy']
        real_sells = [r for r in sells if r['value_eth'] > 0]
        zero_sells = [r for r in sells if r['value_eth'] == 0]
        se = sum(r['value_eth'] for r in sells)
        be = sum(r['value_eth'] for r in buys)
        if tn == 'GVC':
            ns = len(real_sells)
            nt = len(zero_sells)
            print(f'    {tn}: {ns} NFTs sold ({se:.4f} ETH), {nt} transfers, {len(buys)} buys ({be:.4f} ETH)', flush=True)
        else:
            print(f'    {tn}: {len(real_sells)} sells ({se:.4f} ETH), {len(zero_sells)} zero-val, {len(buys)} buys ({be:.4f} ETH)', flush=True)

    return results


def main():
    print('=' * 50, flush=True)
    print('ETHERSCAN FAST FETCH - All 5 Wallets', flush=True)
    print('=' * 50, flush=True)

    all_data = []

    for wallet_addr, wallet_name in WALLETS.items():
        print(f'\n{"=" * 40}', flush=True)
        print(f'WALLET: {wallet_name}', flush=True)
        print(f'{"=" * 40}', flush=True)

        results = process_wallet(wallet_addr, wallet_name)
        all_data.extend(results)

        os.makedirs('data', exist_ok=True)
        with open('data/sells_data.json', 'w') as f:
            json.dump(all_data, f, indent=2, default=str)
        print(f'  Saved ({len(all_data)} total records)', flush=True)

    # Final
    print(f'\n{"=" * 50}', flush=True)
    print('COMPLETE', flush=True)
    print(f'{"=" * 50}', flush=True)
    for tn in ['VIBESTR', 'GVC']:
        td = [r for r in all_data if r['token'] == tn]
        sells = [r for r in td if r['type'] == 'sell']
        buys = [r for r in td if r['type'] == 'buy']
        real_sells = [r for r in sells if r['value_eth'] > 0]
        se = sum(r['value_eth'] for r in sells)
        be = sum(r['value_eth'] for r in buys)
        if tn == 'GVC':
            ns = len(real_sells)
            print(f'  {tn}: {ns} NFTs sold = {se:.4f} ETH, {len(buys)} buys = {be:.4f} ETH', flush=True)
        else:
            print(f'  {tn}: {len(real_sells)} sells = {se:.4f} ETH, {len(buys)} buys = {be:.4f} ETH', flush=True)

        for wn in ['IKZ1', 'DGMD22', 'EraOfVibes', 'Extra25', 'InvestmentFund1']:
            ws = [r for r in td if r['wallet_name'] == wn and r['type'] == 'sell']
            wb = [r for r in td if r['wallet_name'] == wn and r['type'] == 'buy']
            if ws or wb:
                wse = sum(r['value_eth'] for r in ws)
                wbe = sum(r['value_eth'] for r in wb)
                real = [r for r in ws if r['value_eth'] > 0]
                print(f'    {wn}: {len(real)} sells ({wse:.4f} ETH), {len(wb)} buys ({wbe:.4f} ETH)', flush=True)

    print(f'\n  API requests: {REQ_COUNT}', flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
