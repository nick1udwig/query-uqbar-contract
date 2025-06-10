#!/usr/bin/env python3
"""
Script to query UqbarDAO smart contract for uqAlloc values.
Supports both individual addresses and CSV input files.
"""

import argparse
import csv
import json
import sys
from typing import List, Tuple
from web3 import Web3
from web3.exceptions import ContractLogicError, Web3Exception

# Contract details
CONTRACT_ADDRESS = "0x777172385ac1d2e4ac61a9a98b0686cb4701b3a7"
OPTIMISM_RPC_URL = "https://mainnet.optimism.io"  # Default public RPC

# Contract ABI (only the parts we need)
CONTRACT_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "uqAlloc",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

def setup_web3(rpc_url: str) -> Web3:
    """Initialize Web3 connection."""
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            raise ConnectionError("Failed to connect to Ethereum node")
        return w3
    except Exception as e:
        print(f"Error connecting to RPC endpoint: {e}")
        sys.exit(1)

def load_addresses_from_csv(csv_path: str) -> List[str]:
    """Load addresses from CSV file."""
    addresses = []
    try:
        with open(csv_path, 'r', newline='') as csvfile:
            # Try to detect if there's a header
            sample = csvfile.read(1024)
            csvfile.seek(0)
            sniffer = csv.Sniffer()
            has_header = sniffer.has_header(sample)

            reader = csv.reader(csvfile)
            if has_header:
                next(reader)  # Skip header row

            for row in reader:
                if row:  # Skip empty rows
                    address = row[0].strip()
                    if address:
                        addresses.append(address)
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)

    return addresses

def validate_address(address: str) -> bool:
    """Validate Ethereum address format."""
    try:
        return Web3.is_address(address)
    except:
        return False

def query_uq_alloc(contract, address: str) -> Tuple[str, int, str]:
    """
    Query uqAlloc for a given address.
    Returns tuple of (address, allocation, status)
    """
    try:
        if not validate_address(address):
            return address, 0, "Invalid address format"

        # Convert address to checksum format
        checksum_address = Web3.to_checksum_address(address)

        # Call the contract function
        allocation = contract.functions.uqAlloc(checksum_address).call()

        return checksum_address, allocation, "Success"

    except ContractLogicError as e:
        return address, 0, f"Contract error: {e}"
    except Web3Exception as e:
        return address, 0, f"Web3 error: {e}"
    except Exception as e:
        return address, 0, f"Error: {e}"

def write_results_to_csv(results: List[Tuple[str, int, str]], output_path: str):
    """Write results to CSV file."""
    try:
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['address', 'uq_allocation', 'status'])
            writer.writerows(results)
        print(f"Results written to {output_path}")
    except Exception as e:
        print(f"Error writing to CSV: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Query UqbarDAO smart contract for uqAlloc values",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query individual addresses
  python uqbar_dao_query.py --addresses 0x123... 0x456... --output-csv results.csv

  # Query from CSV file
  python uqbar_dao_query.py --csv-file addresses.csv --output-csv results.csv

  # Query and print to console
  python uqbar_dao_query.py --addresses 0x123... 0x456...

  # Use custom RPC endpoint
  python uqbar_dao_query.py --csv-file addresses.csv --rpc-url https://opt-mainnet.g.alchemy.com/v2/YOUR_KEY
        """
    )

    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--addresses',
        nargs='+',
        help='List of Ethereum addresses to query'
    )
    input_group.add_argument(
        '--csv-file',
        help='Path to CSV file containing addresses (first column)'
    )

    # Output options
    parser.add_argument(
        '--output-csv',
        help='Output results to CSV file'
    )

    # RPC configuration
    parser.add_argument(
        '--rpc-url',
        default=OPTIMISM_RPC_URL,
        help=f'Optimism RPC endpoint URL (default: {OPTIMISM_RPC_URL})'
    )

    args = parser.parse_args()

    # Load addresses
    if args.addresses:
        addresses = args.addresses
    else:
        addresses = load_addresses_from_csv(args.csv_file)

    if not addresses:
        print("No addresses to query")
        sys.exit(1)

    print(f"Loaded {len(addresses)} addresses to query")

    # Setup Web3 connection
    print(f"Connecting to Optimism network...")
    w3 = setup_web3(args.rpc_url)

    # Initialize contract
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=CONTRACT_ABI
    )

    # Query each address
    print("Querying contract...")
    results = []

    for i, address in enumerate(addresses, 1):
        print(f"Querying {i}/{len(addresses)}: {address}")
        result = query_uq_alloc(contract, address)
        results.append(result)

    # Output results
    if args.output_csv:
        write_results_to_csv(results, args.output_csv)
    else:
        print("\n" + "="*80)
        print("RESULTS:")
        print("="*80)
        print(f"{'Address':<45} {'Allocation':<15} {'Status'}")
        print("-"*80)

        for address, allocation, status in results:
            if status == "Success":
                # Convert from wei if needed (assuming allocation is in base units)
                print(f"{address:<45} {allocation:<15} {status}")
            else:
                print(f"{address:<45} {'N/A':<15} {status}")

    # Summary
    successful_queries = sum(1 for _, _, status in results if status == "Success")
    total_allocation = sum(allocation for _, allocation, status in results if status == "Success")

    print(f"\nSummary:")
    print(f"  Total addresses queried: {len(results)}")
    print(f"  Successful queries: {successful_queries}")
    print(f"  Failed queries: {len(results) - successful_queries}")
    print(f"  Total allocation found: {total_allocation}")

if __name__ == "__main__":
    main()
