import os
import json
import time
from web3 import Web3
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Get env variables
provider_url = os.getenv('TAIKO_RPC_URL')
if not provider_url:
    raise ValueError("TAIKO_RPC_URL not found in .env")

private_key = os.getenv('PRIVATE_KEY')
if not private_key:
    raise ValueError("PRIVATE_KEY not found in .env")

contract_address = os.getenv('CONTRACT_ADDRESS')
if not contract_address:
    raise ValueError("CONTRACT_ADDRESS not found in .env")

lending_pool = os.getenv('LENDING_POOL')
if not lending_pool:
    raise ValueError("LENDING_POOL not found in .env")

# Setup Web3
w3 = Web3(Web3.HTTPProvider(provider_url))
wallet = w3.eth.account.from_key(private_key)

on_behalf_of = wallet.address
to = wallet.address
referral_code = 0
amount = w3.to_wei(0.4, 'ether')  # ETH per tx
TOTAL_TX = 110  # Total transactions

# Contract ABI (depositETH & withdrawETH)
abi = [
    {
        "inputs": [
            {"internalType": "address", "name": "lendingPool", "type": "address"},
            {"internalType": "address", "name": "onBehalfOf", "type": "address"},
            {"internalType": "uint16", "name": "referralCode", "type": "uint16"}
        ],
        "name": "depositETH",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "lendingPool", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "address", "name": "to", "type": "address"}
        ],
        "name": "withdrawETH",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

contract = w3.eth.contract(address=contract_address, abi=abi)

def save_transaction_status(deposit_counter, withdraw_counter, total_tx):
    status = {
        'deposit_counter': deposit_counter,
        'withdraw_counter': withdraw_counter,
        'total_tx': total_tx
    }
    with open('transaction_status.json', 'w') as f:
        json.dump(status, f)

def load_transaction_status():
    try:
        with open('transaction_status.json', 'r') as f:
            status = json.load(f)
        return status['deposit_counter'], status['withdraw_counter'], status['total_tx']
    except (FileNotFoundError, json.JSONDecodeError):
        return 0, 0, 0

def deposit_eth(amount_in_wei, max_priority_fee_per_gas_gwei=0.015, max_fee_per_gas_gwei=0.015):
    try:
        start_time = time.time()
        max_priority_fee_per_gas = w3.to_wei(max_priority_fee_per_gas_gwei, 'gwei')
        if max_fee_per_gas_gwei is None:
            base_fee = w3.eth.get_block('latest')['baseFeePerGas']
            max_fee_per_gas = base_fee + max_priority_fee_per_gas
        else:
            max_fee_per_gas = w3.to_wei(max_fee_per_gas_gwei, 'gwei')

        gas_estimate = contract.functions.depositETH(lending_pool, on_behalf_of, referral_code).estimate_gas({
            'from': wallet.address,
            'value': amount_in_wei
        })
        gas_limit = int(gas_estimate * 1.2)

        tx = contract.functions.depositETH(lending_pool, on_behalf_of, referral_code).build_transaction({
            'from': wallet.address,
            'value': amount_in_wei,
            'gas': gas_limit,
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': max_priority_fee_per_gas,
            'nonce': w3.eth.get_transaction_count(wallet.address)
        })
        signed_tx = wallet.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_hash.hex(), time.time() - start_time
    except Exception as e:
        print(f"Deposit ETH error: {e}")
        return None, 0

def withdraw_eth(amount_in_wei, max_priority_fee_per_gas_gwei=0.011, max_fee_per_gas_gwei=0.011):
    try:
        start_time = time.time()
        max_priority_fee_per_gas = w3.to_wei(max_priority_fee_per_gas_gwei, 'gwei')
        if max_fee_per_gas_gwei is None:
            base_fee = w3.eth.get_block('latest')['baseFeePerGas']
            max_fee_per_gas = base_fee + max_priority_fee_per_gas
        else:
            max_fee_per_gas = w3.to_wei(max_fee_per_gas_gwei, 'gwei')

        gas_estimate = contract.functions.withdrawETH(lending_pool, amount_in_wei, to).estimate_gas({
            'from': wallet.address
        })
        gas_limit = int(gas_estimate * 1.2)

        tx = contract.functions.withdrawETH(lending_pool, amount_in_wei, to).build_transaction({
            'from': wallet.address,
            'gas': gas_limit,
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': max_priority_fee_per_gas,
            'nonce': w3.eth.get_transaction_count(wallet.address)
        })
        signed_tx = wallet.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_hash.hex(), time.time() - start_time
    except Exception as e:
        print(f"Withdraw ETH error: {e}")
        return None, 0

def print_transaction_status(transaction_type, tx_hash, execution_time, deposit_counter, withdraw_counter, total_tx):
    print("=" * 50)
    print(f"{transaction_type} ETH succeeded")
    print(f"Transaction Hash: {tx_hash}")
    print(f"Execution Time: {execution_time:.2f} seconds")
    print(f"Total Transactions: {total_tx} (Deposit: {deposit_counter}, Withdraw: {withdraw_counter})")
    print("=" * 50)

deposit_counter, withdraw_counter, total_tx = load_transaction_status()

while total_tx < TOTAL_TX:
    if deposit_counter < 55 and total_tx < TOTAL_TX:
        tx_hash, execution_time = deposit_eth(amount, max_priority_fee_per_gas_gwei=0.015)
        if tx_hash:
            deposit_counter += 1
            total_tx += 1
            print_transaction_status("Deposit", tx_hash, execution_time, deposit_counter, withdraw_counter, total_tx)
            save_transaction_status(deposit_counter, withdraw_counter, total_tx)

    if withdraw_counter < 55 and total_tx < TOTAL_TX:
        tx_hash, execution_time = withdraw_eth(amount, max_priority_fee_per_gas_gwei=0.011)
        if tx_hash:
            withdraw_counter += 1
            total_tx += 1
            print_transaction_status("Withdraw", tx_hash, execution_time, deposit_counter, withdraw_counter, total_tx)
            save_transaction_status(deposit_counter, withdraw_counter, total_tx)

    if total_tx >= TOTAL_TX:
        if os.path.exists('transaction_status.json'):
            os.remove('transaction_status.json')
            print("Status: Transaction status file deleted after reaching total transactions.")
        break

    time.sleep(3)
