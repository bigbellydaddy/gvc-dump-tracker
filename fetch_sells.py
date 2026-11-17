#!/usr/bin/env python3
"""
Fetch all sells for DGMD's wallets - VIBESTR + GVC.
Optimized: cached tx lookups, NFT-first value check, faster delays.
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from collections import defaultdict
import os
import sys

WALLETS = {
    '0xb206a73f101071f7a5027275ef52f827b2ea2b11': 'IKZ1',
    '0x2d13c884c4c418664abb1b4a7f491dd89247e42e': 'DGMD22',
    '0x662307a93bce119539a81408186bba28f01613cf': 'EraOfVibes',
    '0x83e574af1bf5813f8552d434b213548e6bd4f35d': 'Extra25',
    '0xa1862a515fe0d692392fd1e51d7aeab674a6864b': 'InvestmentFund1'
}

WALLET_SET = set(w.lower() for w in WALLETS.keys())

TOKENS = {
    'VIBESTR': {
        'address': '0xd0cc2b0efb168bfe1f94a948d8df70fa10257196',
        'baseUrl': 'https://eth.blockscout.com/api/v2',
        'decimals': 18,
        'isNFT': False,
        'track': 'both'
    },
    'GVC': {
        'address': '0xb8ea78fcacef50d41375e44e6814ebba36bb33c4',
        'baseUrl': 'https://eth.blockscout.com/api/v2',
        'decimals': 0,
        'isNFT': True,
        'track': 'both'
    }
}

REQUEST_COUNT = 0
LAST_REQUEST_TIME = 0
TX_CACHE = {}


def api_fetch(url, retries=5, delay=1.5):
    global REQUEST_COUNT, LAST_REQUEST_TIME
    elapsed = time.time() - LAST_REQUEST_TIME
    if elapsed < delay:
        time.sleep(delay - elapsed)

    for attempt in range(retries):
        try:
            REQUEST_COUNT += 1
            LAST_REQUEST_TIME = time.time()
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 6 * (attempt + 1)
                print(f'    429 rate limited, waiting {wait}s...', flush=True)
                time.sleep(wait)
            elif e.code == 404:
                return None
            else:
                print(f'    HTTP {e.code}, retry {attempt+1}...', flush=True)
                time.sleep(2)
        except Exception as e:
            msg = str(e)
            if 'timed out' in msg:
                print(f'    Timeout, retry {attempt+1}...', flush=True)
            else:
                print(f'    {msg[:60]}, retry {attempt+1}...', flush=True)
            time.sleep(2)
    print(f'    FAILED after {retries} retries', flush=True)
    return None


def fetch_all_token_transfers(base_url, wallet, token_addr):
    all_items = []
    next_params = None
    page = 0
    while True:
        page += 1
        url = f'{base_url}/addresses/{wallet}/token-transfers?token={token_addr}&type=ERC-20,ERC-721,ERC-1155'
        if next_params:
            url += '&' + '&'.join(f'{k}={v}' for k, v in next_params.items())
        data = api_fetch(url)
        if not data:
            break
        items = data.get('items', [])
        if not items:
            break
        all_items.extend(items)
        print(f'      Page {page}: +{len(items)} (total: {len(all_items)})', flush=True)
        next_params = data.get('next_page_params')
        if not next_params or page > 50:
            break
    return all_items


def get_tx_details(base_url, tx_hash):
    key = ('details', tx_hash)
    if key in TX_CACHE:
        return TX_CACHE[key]
    result = api_fetch(f'{base_url}/transactions/{tx_hash}')
    TX_CACHE[key] = result
    return result


def get_tx_token_transfers(base_url, tx_hash):
    key = ('transfers', tx_hash)
    if key in TX_CACHE:
        return TX_CACHE[key]
    all_items = []
    next_params = None
    while True:
        url = f'{base_url}/transactions/{tx_hash}/token-transfers'
        if next_params:
            url += '&' + '&'.join(f'{k}={v}' for k, v in next_params.items())
        data = api_fetch(url)
        if not data:
            break
        all_items.extend(data.get('items', []))
        next_params = data.get('next_page_params')
        if not next_params:
            break
    TX_CACHE[key] = all_items
    return all_items


def get_internal_txs(base_url, tx_hash):
    key = ('internal', tx_hash)
    if key in TX_CACHE:
        return TX_CACHE[key]
    data = api_fetch(f'{base_url}/transactions/{tx_hash}/internal-transactions')
    result = data.get('items', []) if data else []
    TX_CACHE[key] = result
    return result


def find_value(base_url, tx_hash, wallet_lower, is_sell, is_nft):
    value_eth = 0.0

    # For NFTs: check main tx value FIRST (cheapest call, often has OpenSea sale price)
    if is_nft:
        tx_data = get_tx_details(base_url, tx_hash)
        if tx_data:
            native_eth = float(tx_data.get('value', '0')) / 1e18
            if native_eth > 0.001:
                return native_eth

    # Check token transfers for WETH/ETH going to/from wallet
    tx_transfers = get_tx_token_transfers(base_url, tx_hash)
    for t in tx_transfers:
        sym = (t.get('token', {}).get('symbol', '') or '').lower()
        if sym not in ('weth', 'eth'):
            continue
        t_to = (t.get('to', {}).get('hash', '') or '').lower()
        t_from = (t.get('from', {}).get('hash', '') or '').lower()
        dec = int(t.get('total', {}).get('decimals', '') or 18)
        amt = float(t.get('total', {}).get('value', '0')) / (10 ** dec)
        if amt == 0:
            continue
        if is_sell and t_to == wallet_lower and amt > value_eth:
            value_eth = amt
        elif not is_sell and t_from == wallet_lower and amt > value_eth:
            value_eth = amt

    if value_eth > 0:
        return value_eth

    # Check internal transactions (Uniswap V3 unwraps WETH to native ETH)
    internal_txs = get_internal_txs(base_url, tx_hash)
    for itx in internal_txs:
        itx_to = (itx.get('to', {}).get('hash', '') or '').lower()
        itx_from = (itx.get('from', {}).get('hash', '') or '').lower()
        itx_val = float(itx.get('value', '0')) / 1e18
        if itx_val < 0.0001:
            continue
        if is_sell and itx_to == wallet_lower and itx_val > value_eth:
            value_eth = itx_val
        elif not is_sell and itx_from == wallet_lower and itx_val > value_eth:
            value_eth = itx_val

    # For non-NFT tokens, also check tx value as last resort
    if value_eth == 0 and not is_nft:
        tx_data = get_tx_details(base_url, tx_hash)
        if tx_data:
            native_eth = float(tx_data.get('value', '0')) / 1e18
            if native_eth > 0.001:
                value_eth = native_eth

    return value_eth


def process_wallet_token(wallet_addr, wallet_name, token_name, token_info):
    global TX_CACHE
    TX_CACHE = {}  # Clear cache between wallet+token combos

    base_url = token_info['baseUrl']
    is_nft = token_info.get('isNFT', False)
    track = token_info.get('track', 'both')

    print(f'  Fetching {token_name} transfers...', flush=True)
    transfers = fetch_all_token_transfers(base_url, wallet_addr, token_info['address'])
    print(f'    Total transfers: {len(transfers)}', flush=True)

    if not transfers:
        return []

    by_tx = defaultdict(list)
    for t in transfers:
        by_tx[t.get('transaction_hash', '')].append(t)

    print(f'    Unique transactions: {len(by_tx)}', flush=True)

    results = []
    wallet_lower = wallet_addr.lower()
    lookup_count = 0

    for tx_hash, tx_transfers_local in by_tx.items():
        # Classify all transfers in this tx at once
        relevant = []
        for tt in tx_transfers_local:
            from_addr = (tt.get('from', {}).get('hash', '') or '').lower()
            to_addr = (tt.get('to', {}).get('hash', '') or '').lower()
            if from_addr in WALLET_SET and to_addr in WALLET_SET:
                continue
            is_sell = from_addr == wallet_lower
            is_buy = to_addr == wallet_lower
            if not is_sell and not is_buy:
                continue
            if track == 'sells_only' and not is_sell:
                continue
            relevant.append((tt, is_sell, is_buy))

        if not relevant:
            continue

        lookup_count += 1
        if lookup_count % 10 == 0:
            print(f'    Looked up {lookup_count} unique txs...', flush=True)

        # Look up value ONCE per tx (cached anyway, but this is cleaner)
        # Use the first relevant transfer to determine sell/buy for value lookup
        first_sell = any(s for _, s, _ in relevant if s)
        value_eth = find_value(base_url, tx_hash, wallet_lower, first_sell, is_nft)

        for tt, is_sell, is_buy in relevant:
            if is_nft:
                token_type = tt.get('token', {}).get('type', '')
                if token_type == 'ERC-1155':
                    dec = int(tt.get('total', {}).get('decimals', '') or 0)
                    amount = float(tt.get('total', {}).get('value', '1')) / (10 ** dec) if dec > 0 else float(tt.get('total', {}).get('value', '1'))
                else:
                    amount = 1
            else:
                dec = int(tt.get('total', {}).get('decimals', '') or token_info['decimals'])
                amount = float(tt.get('total', {}).get('value', '0')) / (10 ** dec)

            if amount == 0 and not is_nft:
                continue

            timestamp = tt.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                date_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                date_str = 'unknown'

            # For batch NFT sales in same tx, divide value by count
            nft_count_in_tx = sum(1 for _, s, _ in relevant if s == is_sell) if is_nft else 1
            per_item_eth = value_eth / nft_count_in_tx if nft_count_in_tx > 0 else value_eth

            results.append({
                'date': date_str,
                'type': 'sell' if is_sell else 'buy',
                'amount': amount,
                'value_eth': per_item_eth,
                'tx_hash': tx_hash,
                'wallet': wallet_addr,
                'wallet_name': wallet_name,
                'token': token_name
            })

    sells = [r for r in results if r['type'] == 'sell']
    buys = [r for r in results if r['type'] == 'buy']
    sell_eth = sum(r['value_eth'] for r in sells)
    buy_eth = sum(r['value_eth'] for r in buys)
    nft_sold = sum(int(r['amount']) for r in sells) if is_nft else len(sells)

    if is_nft:
        print(f'    Results: {nft_sold} NFTs sold ({sell_eth:.4f} ETH), {len(buys)} buys ({buy_eth:.4f} ETH)', flush=True)
    else:
        print(f'    Results: {len(sells)} sells ({sell_eth:.4f} ETH), {len(buys)} buys ({buy_eth:.4f} ETH)', flush=True)

    return results


def save_progress(all_data):
    os.makedirs('data', exist_ok=True)
    with open('data/sells_data.json', 'w') as f:
        json.dump(all_data, f, indent=2, default=str)


def main():
    print('=' * 50, flush=True)
    print('DGMD SELLS - VIBESTR + GVC (Optimized)', flush=True)
    print('=' * 50, flush=True)

    print('\nFetching ETH price...', flush=True)
    try:
        data = api_fetch('https://api.dexscreener.com/latest/dex/tokens/0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
        eth_price = 1800
        if data and data.get('pairs'):
            for p in data['pairs']:
                if p.get('quoteToken', {}).get('symbol') == 'USDT':
                    eth_price = float(p['priceUsd'])
                    break
            if eth_price == 1800:
                eth_price = float(data['pairs'][0].get('priceUsd', 1800))
    except:
        eth_price = 1800
    print(f'  ETH = ${eth_price:,.0f}', flush=True)

    all_data = []

    for wallet_addr, wallet_name in WALLETS.items():
        print(f'\n{"=" * 40}', flush=True)
        print(f'WALLET: {wallet_name} ({wallet_addr[:12]}...)', flush=True)
        print(f'{"=" * 40}', flush=True)

        for token_name, token_info in TOKENS.items():
            print(f'\n  --- {token_name} ---', flush=True)
            results = process_wallet_token(wallet_addr, wallet_name, token_name, token_info)
            all_data.extend(results)
            save_progress(all_data)
            print(f'  Saved ({len(all_data)} total records)', flush=True)
            time.sleep(1)

    save_progress(all_data)

    print(f'\n{"=" * 50}', flush=True)
    print('SUMMARY', flush=True)
    print(f'{"=" * 50}', flush=True)

    token_summary = defaultdict(lambda: {'sells': 0, 'sell_eth': 0, 'buys': 0, 'buy_eth': 0, 'nft_sold': 0})
    for tx in all_data:
        t = token_summary[tx['token']]
        if tx['type'] == 'sell':
            t['sells'] += 1
            t['sell_eth'] += tx['value_eth']
            t['nft_sold'] += int(tx['amount']) if tx['token'] == 'GVC' else 0
        else:
            t['buys'] += 1
            t['buy_eth'] += tx['value_eth']

    grand = 0
    for tn in ['VIBESTR', 'GVC']:
        d = token_summary[tn]
        extra = f' ({d["nft_sold"]} NFTs)' if tn == 'GVC' else ''
        print(f'  {tn}: {d["sells"]} sells{extra} = {d["sell_eth"]:.4f} ETH (${d["sell_eth"] * eth_price:,.2f})', flush=True)
        if d['buys'] > 0:
            print(f'         {d["buys"]} buys = {d["buy_eth"]:.4f} ETH', flush=True)
        grand += d['sell_eth']

    print(f'\n  TOTAL SELLS: {grand:.4f} ETH (${grand * eth_price:,.2f})', flush=True)
    print(f'  API requests: {REQUEST_COUNT}', flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
