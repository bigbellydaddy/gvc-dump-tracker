#!/usr/bin/env python3
"""
FAST fetch: Get VIBESTR + GVC data for remaining 4 wallets.
Instead of looking up each tx individually, bulk-fetch all wallet txs
and internal txs, then cross-reference by tx hash.
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from collections import defaultdict
import os

WALLETS = {
    '0x2d13c884c4c418664abb1b4a7f491dd89247e42e': 'DGMD22',
    '0x662307a93bce119539a81408186bba28f01613cf': 'EraOfVibes',
    '0x83e574af1bf5813f8552d434b213548e6bd4f35d': 'Extra25',
    '0xa1862a515fe0d692392fd1e51d7aeab674a6864b': 'InvestmentFund1'
}

ALL_WALLETS = set([
    '0xb206a73f101071f7a5027275ef52f827b2ea2b11',
    '0x2d13c884c4c418664abb1b4a7f491dd89247e42e',
    '0x662307a93bce119539a81408186bba28f01613cf',
    '0x83e574af1bf5813f8552d434b213548e6bd4f35d',
    '0xa1862a515fe0d692392fd1e51d7aeab674a6864b'
])

VIBESTR = '0xd0cc2b0efb168bfe1f94a948d8df70fa10257196'
GVC = '0xb8ea78fcacef50d41375e44e6814ebba36bb33c4'
BASE = 'https://eth.blockscout.com/api/v2'

REQ = 0
LAST = 0


def fetch(url, retries=4, delay=1.5):
    global REQ, LAST
    elapsed = time.time() - LAST
    if elapsed < delay:
        time.sleep(delay - elapsed)
    for attempt in range(retries):
        try:
            REQ += 1
            LAST = time.time()
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            })
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                w = 8 * (attempt + 1)
                print(f'    429 rate limit, wait {w}s', flush=True)
                time.sleep(w)
            elif e.code == 404:
                return None
            else:
                print(f'    HTTP {e.code}, retry {attempt+1}', flush=True)
                time.sleep(3)
        except Exception as e:
            print(f'    {str(e)[:50]}, retry {attempt+1}', flush=True)
            time.sleep(3)
    print(f'    FAILED', flush=True)
    return None


def fetch_pages(url_base, max_pages=100):
    all_items = []
    next_params = None
    for page in range(1, max_pages + 1):
        url = url_base
        if next_params:
            sep = '&' if '?' in url else '?'
            url += sep + '&'.join(f'{k}={v}' for k, v in next_params.items())
        data = fetch(url)
        if not data:
            break
        items = data.get('items', [])
        if not items:
            break
        all_items.extend(items)
        if page % 5 == 0:
            print(f'      Page {page}: {len(all_items)} total', flush=True)
        next_params = data.get('next_page_params')
        if not next_params:
            break
    return all_items


def process_wallet(wallet_addr, wallet_name):
    wallet_lower = wallet_addr.lower()
    print(f'\n  Step 1: Fetch all token transfers (VIBESTR + GVC)...', flush=True)

    vibestr_transfers = fetch_pages(
        f'{BASE}/addresses/{wallet_addr}/token-transfers?token={VIBESTR}&type=ERC-20,ERC-721,ERC-1155'
    )
    print(f'    VIBESTR transfers: {len(vibestr_transfers)}', flush=True)

    gvc_transfers = fetch_pages(
        f'{BASE}/addresses/{wallet_addr}/token-transfers?token={GVC}&type=ERC-20,ERC-721,ERC-1155'
    )
    print(f'    GVC transfers: {len(gvc_transfers)}', flush=True)

    all_token_transfers = vibestr_transfers + gvc_transfers
    if not all_token_transfers:
        print(f'    No transfers found, skipping', flush=True)
        return []

    # Collect tx hashes we need values for
    needed_hashes = set()
    for t in all_token_transfers:
        needed_hashes.add(t.get('transaction_hash', ''))
    needed_hashes.discard('')
    print(f'    Unique tx hashes to resolve: {len(needed_hashes)}', flush=True)

    # Step 2: Bulk fetch - get all wallet transactions (has tx value)
    print(f'  Step 2: Bulk fetch wallet transactions...', flush=True)
    all_txs = fetch_pages(f'{BASE}/addresses/{wallet_addr}/transactions')
    print(f'    Wallet txs fetched: {len(all_txs)}', flush=True)

    # Build tx hash -> value map
    tx_value_map = {}
    for tx in all_txs:
        h = tx.get('hash', '')
        val = float(tx.get('value', '0')) / 1e18
        tx_value_map[h] = val

    # Step 3: Bulk fetch internal transactions (for Uniswap WETH unwraps)
    print(f'  Step 3: Bulk fetch internal transactions...', flush=True)
    all_internal = fetch_pages(f'{BASE}/addresses/{wallet_addr}/internal-transactions')
    print(f'    Internal txs fetched: {len(all_internal)}', flush=True)

    # Build tx hash -> ETH received via internal txs
    internal_eth_map = defaultdict(float)
    for itx in all_internal:
        h = itx.get('transaction_hash', '')
        to_addr = (itx.get('to', {}).get('hash', '') or '').lower()
        from_addr = (itx.get('from', {}).get('hash', '') or '').lower()
        val = float(itx.get('value', '0')) / 1e18
        if val < 0.0001:
            continue
        if to_addr == wallet_lower:
            internal_eth_map[h] = max(internal_eth_map[h], val)

    # Step 4: Bulk fetch token transfers for all txs (for WETH transfers)
    # Only fetch for tx hashes where we don't have value from main tx or internal
    print(f'  Step 4: Check WETH in token transfers...', flush=True)
    weth_map = defaultdict(float)

    # From the token transfers we already have, check for WETH
    # Also need to check other token transfers in same tx
    hashes_needing_weth = set()
    for h in needed_hashes:
        main_val = tx_value_map.get(h, 0)
        internal_val = internal_eth_map.get(h, 0)
        if main_val < 0.001 and internal_val < 0.001:
            hashes_needing_weth.add(h)

    # For efficiency, fetch token transfers per-tx only for ones we can't resolve
    # But first check if any of our existing transfers have WETH
    for t in all_token_transfers:
        h = t.get('transaction_hash', '')
        sym = (t.get('token', {}).get('symbol', '') or '').lower()
        if sym in ('weth', 'eth'):
            to_addr = (t.get('to', {}).get('hash', '') or '').lower()
            dec = int(t.get('total', {}).get('decimals', '') or 18)
            amt = float(t.get('total', {}).get('value', '0')) / (10 ** dec)
            if to_addr == wallet_lower and amt > weth_map[h]:
                weth_map[h] = amt

    # For remaining unresolved hashes, do individual lookups (but should be few)
    unresolved = []
    for h in hashes_needing_weth:
        if h not in weth_map or weth_map[h] < 0.001:
            unresolved.append(h)

    if unresolved:
        print(f'    {len(unresolved)} txs still need individual WETH lookup...', flush=True)
        for i, h in enumerate(unresolved):
            if i > 0 and i % 10 == 0:
                print(f'      {i}/{len(unresolved)} done...', flush=True)
            data = fetch(f'{BASE}/transactions/{h}/token-transfers')
            if data:
                for t in data.get('items', []):
                    sym = (t.get('token', {}).get('symbol', '') or '').lower()
                    if sym in ('weth', 'eth'):
                        to_addr = (t.get('to', {}).get('hash', '') or '').lower()
                        from_addr = (t.get('from', {}).get('hash', '') or '').lower()
                        dec = int(t.get('total', {}).get('decimals', '') or 18)
                        amt = float(t.get('total', {}).get('value', '0')) / (10 ** dec)
                        if to_addr == wallet_lower and amt > weth_map[h]:
                            weth_map[h] = amt
                        elif from_addr == wallet_lower and amt > weth_map.get(h + '_out', 0):
                            weth_map[h + '_out'] = amt

    # Step 5: Build results
    print(f'  Step 5: Building results...', flush=True)

    # Group token transfers by tx hash
    by_tx = defaultdict(list)
    for t in all_token_transfers:
        by_tx[t.get('transaction_hash', '')].append(t)

    results = []
    for tx_hash, transfers in by_tx.items():
        for tt in transfers:
            from_addr = (tt.get('from', {}).get('hash', '') or '').lower()
            to_addr = (tt.get('to', {}).get('hash', '') or '').lower()

            # Skip inter-wallet transfers
            if from_addr in ALL_WALLETS and to_addr in ALL_WALLETS:
                continue

            is_sell = from_addr == wallet_lower
            is_buy = to_addr == wallet_lower

            if not is_sell and not is_buy:
                continue

            # Determine token
            token_addr = (tt.get('token', {}).get('address_hash', '') or tt.get('token', {}).get('address', '') or '').lower()
            if token_addr == VIBESTR.lower():
                token_name = 'VIBESTR'
                is_nft = False
            elif token_addr == GVC.lower():
                token_name = 'GVC'
                is_nft = True
            else:
                continue

            # Get amount
            if is_nft:
                token_type = tt.get('token', {}).get('type', '')
                if token_type == 'ERC-1155':
                    dec = int(tt.get('total', {}).get('decimals', '') or 0)
                    amount = float(tt.get('total', {}).get('value', '1')) / (10 ** dec) if dec > 0 else float(tt.get('total', {}).get('value', '1'))
                else:
                    amount = 1
            else:
                dec = int(tt.get('total', {}).get('decimals', '') or 18)
                amount = float(tt.get('total', {}).get('value', '0')) / (10 ** dec)

            if amount == 0 and not is_nft:
                continue

            # Get ETH value - check all sources
            value_eth = 0
            if is_sell:
                # For sells: wallet receives ETH
                # Check internal txs first (Uniswap unwraps)
                value_eth = internal_eth_map.get(tx_hash, 0)
                # Check WETH transfers
                if value_eth < 0.001:
                    value_eth = weth_map.get(tx_hash, 0)
                # Check main tx value (NFT sales on OpenSea)
                if value_eth < 0.001 and is_nft:
                    value_eth = tx_value_map.get(tx_hash, 0)
            else:
                # For buys: wallet sends ETH
                value_eth = tx_value_map.get(tx_hash, 0)
                if value_eth < 0.001:
                    value_eth = weth_map.get(tx_hash + '_out', 0)
                if value_eth < 0.001:
                    # Check internal txs where wallet sends ETH
                    for itx in all_internal:
                        if itx.get('transaction_hash', '') == tx_hash:
                            fr = (itx.get('from', {}).get('hash', '') or '').lower()
                            v = float(itx.get('value', '0')) / 1e18
                            if fr == wallet_lower and v > value_eth:
                                value_eth = v

            # For batch NFT sales, divide by count in same tx
            if is_nft:
                same_dir = [t for t in transfers
                           if ((t.get('from', {}).get('hash', '') or '').lower() == wallet_lower) == is_sell
                           and (t.get('token', {}).get('address', '') or '').lower() == token_addr.lower()]
                if len(same_dir) > 1 and value_eth > 0:
                    value_eth = value_eth / len(same_dir)

            timestamp = tt.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                date_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                date_str = 'unknown'

            results.append({
                'date': date_str,
                'type': 'sell' if is_sell else 'buy',
                'amount': amount,
                'value_eth': value_eth,
                'tx_hash': tx_hash,
                'wallet': wallet_addr,
                'wallet_name': wallet_name,
                'token': token_name
            })

    # Summary
    for tn in ['VIBESTR', 'GVC']:
        td = [r for r in results if r['token'] == tn]
        sells = [r for r in td if r['type'] == 'sell']
        buys = [r for r in td if r['type'] == 'buy']
        real_sells = [r for r in sells if r['value_eth'] > 0]
        zero_sells = [r for r in sells if r['value_eth'] == 0]
        se = sum(r['value_eth'] for r in sells)
        be = sum(r['value_eth'] for r in buys)
        if tn == 'GVC':
            ns = sum(int(r['amount']) for r in real_sells)
            nt = sum(int(r['amount']) for r in zero_sells)
            print(f'    {tn}: {ns} NFTs sold ({se:.4f} ETH), {nt} transfers, {len(buys)} buys ({be:.4f} ETH)', flush=True)
        else:
            print(f'    {tn}: {len(real_sells)} sells ({se:.4f} ETH), {len(zero_sells)} zero-val, {len(buys)} buys ({be:.4f} ETH)', flush=True)

    return results


def main():
    print('=' * 50, flush=True)
    print('FAST FETCH - Remaining 4 Wallets', flush=True)
    print('Bulk approach: fetch all txs + internal at once', flush=True)
    print('=' * 50, flush=True)

    # Load existing IKZ1 data
    existing = []
    if os.path.exists('data/sells_data.json'):
        with open('data/sells_data.json') as f:
            existing = json.load(f)
        # Keep only IKZ1 data
        existing = [r for r in existing if r.get('wallet_name') == 'IKZ1']
        print(f'Loaded {len(existing)} IKZ1 records', flush=True)

    all_data = list(existing)

    for wallet_addr, wallet_name in WALLETS.items():
        print(f'\n{"=" * 40}', flush=True)
        print(f'WALLET: {wallet_name} ({wallet_addr[:12]}...)', flush=True)
        print(f'{"=" * 40}', flush=True)

        results = process_wallet(wallet_addr, wallet_name)
        all_data.extend(results)

        os.makedirs('data', exist_ok=True)
        with open('data/sells_data.json', 'w') as f:
            json.dump(all_data, f, indent=2, default=str)
        print(f'  Saved ({len(all_data)} total records)', flush=True)

    # Final summary
    print(f'\n{"=" * 50}', flush=True)
    print('COMPLETE - All 5 Wallets', flush=True)
    print(f'{"=" * 50}', flush=True)
    for tn in ['VIBESTR', 'GVC']:
        td = [r for r in all_data if r['token'] == tn]
        sells = [r for r in td if r['type'] == 'sell']
        buys = [r for r in td if r['type'] == 'buy']
        real_sells = [r for r in sells if r['value_eth'] > 0]
        se = sum(r['value_eth'] for r in sells)
        be = sum(r['value_eth'] for r in buys)
        if tn == 'GVC':
            ns = sum(int(r['amount']) for r in real_sells)
            print(f'  {tn}: {ns} NFTs sold = {se:.4f} ETH, {len(buys)} buys = {be:.4f} ETH', flush=True)
        else:
            print(f'  {tn}: {len(real_sells)} sells = {se:.4f} ETH, {len(buys)} buys = {be:.4f} ETH', flush=True)
    print(f'  API requests: {REQ}', flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
