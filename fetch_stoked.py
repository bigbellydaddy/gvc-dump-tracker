#!/usr/bin/env python3
"""Fetch STOKED sells for all DGMD wallets from Robinhood chain Blockscout."""

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

STOKED_ADDR = '0xb76b35647cabf3b6aaf90fec374c58038478d12f'
BASE_URL = 'https://robinhoodchain.blockscout.com/api/v2'

REQUEST_COUNT = 0
LAST_REQUEST_TIME = 0


def api_fetch(url, retries=5, delay_between=2.0):
    global REQUEST_COUNT, LAST_REQUEST_TIME
    elapsed = time.time() - LAST_REQUEST_TIME
    if elapsed < delay_between:
        time.sleep(delay_between - elapsed)

    for attempt in range(retries):
        try:
            REQUEST_COUNT += 1
            LAST_REQUEST_TIME = time.time()
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 10 * (attempt + 1)
                print(f'    429 rate limited, waiting {wait}s...', flush=True)
                time.sleep(wait)
            elif e.code == 404:
                return None
            elif e.code == 403:
                print(f'    403 Cloudflare blocked! Waiting 30s...', flush=True)
                time.sleep(30)
            else:
                print(f'    HTTP {e.code}, retrying in 5s...', flush=True)
                time.sleep(5)
        except Exception as e:
            print(f'    Error: {e}, retrying in 5s...', flush=True)
            time.sleep(5)
    print(f'    FAILED after {retries} retries', flush=True)
    return None


def fetch_all_transfers(wallet):
    all_items = []
    next_params = None
    page = 0

    while True:
        page += 1
        url = f'{BASE_URL}/addresses/{wallet}/token-transfers?token={STOKED_ADDR}&type=ERC-20'
        if next_params:
            params = '&'.join(f'{k}={v}' for k, v in next_params.items())
            url += '&' + params

        data = api_fetch(url)
        if not data:
            break

        items = data.get('items', [])
        if not items:
            break

        all_items.extend(items)
        print(f'      Page {page}: +{len(items)} (total: {len(all_items)})', flush=True)

        next_params = data.get('next_page_params')
        if not next_params:
            break
        if page > 50:
            break

    return all_items


def fetch_tx_token_transfers(tx_hash):
    all_items = []
    next_params = None
    while True:
        url = f'{BASE_URL}/transactions/{tx_hash}/token-transfers'
        if next_params:
            params = '&'.join(f'{k}={v}' for k, v in next_params.items())
            url += '&' + params
        data = api_fetch(url)
        if not data:
            break
        items = data.get('items', [])
        all_items.extend(items)
        next_params = data.get('next_page_params')
        if not next_params:
            break
    return all_items


def find_eth_value(tx_hash, wallet_lower, is_sell):
    """Find the ETH value in a STOKED swap transaction.
    Robinhood chain pattern: aggregator collects WETH, burns it (sends to 0x000...),
    native ETH goes to wallet. Some sells route to USDG instead."""
    value_eth = 0.0
    value_usd = 0.0

    transfers = fetch_tx_token_transfers(tx_hash)

    # Step 1: Check if wallet directly received WETH/ETH
    for t in transfers:
        sym = (t.get('token', {}).get('symbol', '') or '').lower()
        if sym not in ('weth', 'eth'):
            continue
        t_to = (t.get('to', {}).get('hash', '') or '').lower()
        dec = int(t.get('total', {}).get('decimals', '') or 18)
        amt = float(t.get('total', {}).get('value', '0')) / (10 ** dec)
        if amt == 0:
            continue
        if is_sell and t_to == wallet_lower and amt > value_eth:
            value_eth = amt

    # Step 2: Check for WETH burned (unwrapped to native ETH)
    if value_eth == 0:
        for t in transfers:
            sym = (t.get('token', {}).get('symbol', '') or '').lower()
            if sym not in ('weth', 'eth'):
                continue
            t_to = (t.get('to', {}).get('hash', '') or '').lower()
            dec = int(t.get('total', {}).get('decimals', '') or 18)
            amt = float(t.get('total', {}).get('value', '0')) / (10 ** dec)
            if amt > 0 and t_to.startswith('0x00000000') and amt > value_eth:
                value_eth = amt

    # Step 3: Check if wallet received USDG/stablecoins instead of ETH
    if value_eth == 0:
        for t in transfers:
            sym = (t.get('token', {}).get('symbol', '') or '').lower()
            if sym not in ('usdg', 'usdc', 'usdt', 'dai'):
                continue
            t_to = (t.get('to', {}).get('hash', '') or '').lower()
            dec = int(t.get('total', {}).get('decimals', '') or 18)
            amt = float(t.get('total', {}).get('value', '0')) / (10 ** dec)
            if amt > 0 and t_to == wallet_lower and amt > value_usd:
                value_usd = amt

    return value_eth, value_usd


def main():
    print('=' * 50, flush=True)
    print('STOKED SELLS - Robinhood Chain Blockscout', flush=True)
    print('(with WETH burn + USDG detection)', flush=True)
    print('=' * 50, flush=True)

    all_data = []

    for wallet_addr, wallet_name in WALLETS.items():
        print(f'\nWALLET: {wallet_name} ({wallet_addr[:12]}...)', flush=True)

        transfers = fetch_all_transfers(wallet_addr)
        print(f'  Total transfers: {len(transfers)}', flush=True)

        if not transfers:
            print(f'  No STOKED transfers found', flush=True)
            continue

        by_tx = defaultdict(list)
        for t in transfers:
            by_tx[t.get('transaction_hash', '')].append(t)

        wallet_lower = wallet_addr.lower()
        lookup_count = 0

        for tx_hash, tx_transfers in by_tx.items():
            for tt in tx_transfers:
                from_addr = (tt.get('from', {}).get('hash', '') or '').lower()
                to_addr = (tt.get('to', {}).get('hash', '') or '').lower()

                if from_addr in WALLET_SET and to_addr in WALLET_SET:
                    continue

                is_sell = from_addr == wallet_lower
                if not is_sell:
                    continue

                dec = 18
                amount = float(tt.get('total', {}).get('value', '0')) / (10 ** dec)
                if amount == 0:
                    continue

                lookup_count += 1
                if lookup_count % 5 == 0:
                    print(f'    Looking up tx values... ({lookup_count} done)', flush=True)

                value_eth, value_usd = find_eth_value(tx_hash, wallet_lower, is_sell=True)

                timestamp = tt.get('timestamp', '')
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    date_str = 'unknown'

                all_data.append({
                    'date': date_str,
                    'type': 'sell',
                    'amount': amount,
                    'value_eth': value_eth,
                    'value_usd': value_usd,
                    'value_token': 'ETH' if value_eth > 0 else ('USDG' if value_usd > 0 else 'unknown'),
                    'tx_hash': tx_hash,
                    'wallet': wallet_addr,
                    'wallet_name': wallet_name,
                    'token': 'STOKED'
                })

        sells = [r for r in all_data if r['wallet_name'] == wallet_name]
        sell_eth = sum(r['value_eth'] for r in sells)
        sell_usd = sum(r['value_usd'] for r in sells)
        print(f'  {wallet_name}: {len(sells)} sells = {sell_eth:.4f} ETH + ${sell_usd:.2f} USDG', flush=True)

        os.makedirs('data', exist_ok=True)
        with open('data/stoked_data.json', 'w') as f:
            json.dump(all_data, f, indent=2, default=str)
        print(f'  Saved progress ({len(all_data)} total records)', flush=True)

        time.sleep(3)

    os.makedirs('data', exist_ok=True)
    with open('data/stoked_data.json', 'w') as f:
        json.dump(all_data, f, indent=2, default=str)

    total_eth = sum(r['value_eth'] for r in all_data)
    total_usd = sum(r['value_usd'] for r in all_data)
    print(f'\n{"=" * 50}', flush=True)
    print(f'STOKED TOTAL: {len(all_data)} sells = {total_eth:.4f} ETH + ${total_usd:.2f} USDG', flush=True)
    print(f'API requests: {REQUEST_COUNT}', flush=True)
    print(f'{"=" * 50}', flush=True)


if __name__ == '__main__':
    main()
