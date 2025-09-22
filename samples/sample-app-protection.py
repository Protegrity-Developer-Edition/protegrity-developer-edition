import argparse
import sys
from appython import Protector


def create_parser():
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Protect and unprotect data using Protegrity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=
        """
        Examples:
        python sample-app-protection.py --input_data "John Smith" --policy_user superuser --data_element name
        python sample-app-protection.py --input_data "john@example.com" --policy_user superuser --data_element email --protect
        python sample-app-protection.py --input_data "protected_data" --policy_user superuser --data_element email --unprotect
        python sample-app-protection.py --input_data "John Smith" --policy_user superuser --data_element text --enc
        python sample-app-protection.py --input_data "encrypted_hex_data" --policy_user superuser --data_element text --dec
        """,
    )

    parser.add_argument(
        "--input_data", 
        required=True,
        help="The data to protect (e.g., 'John Smith')"
    )

    parser.add_argument(
        "--policy_user", 
        required=True,
        help="Policy user for the session (e.g., 'superuser')"
    )

    parser.add_argument(
        "--data_element", 
        required=True,
        help="Data element type (e.g., 'name', 'email')"
    )

    parser.add_argument(
        "--protect",
        action="store_true",
        help="Only perform protect operation"
    )

    parser.add_argument(
        "--unprotect",
        action="store_true",
        help="Only perform unprotect operation"
    )

    parser.add_argument(
        "--enc",
        action="store_true",
        help="Only perform encrypt operation (output in hex format)"
    )

    parser.add_argument(
        "--dec",
        action="store_true",
        help="Only perform decrypt operation"
    )

    return parser


def main():
    """Main function to handle command line arguments and execute protection operations."""
    parser = create_parser()

    # Check if no arguments provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    try:
        args = parser.parse_args()
    except SystemExit:
        # argparse already printed error message
        sys.exit(1)

    input_data = args.input_data
    policy_user = args.policy_user
    data_element = args.data_element

    try:
        # Initialize the protector
        protector = Protector()

        # Create session with policy user
        session = protector.create_session(policy_user)

        # Determine which operations to perform
        should_protect = args.protect or (not args.protect and not args.unprotect and not args.enc and not args.dec)
        should_unprotect = args.unprotect or (not args.protect and not args.unprotect and not args.enc and not args.dec)
        should_encrypt = args.enc
        should_decrypt = args.dec

        protected_data = None
        encrypted_data = None

        # Protect operation
        if should_protect:
            protected_data = session.protect(input_data, data_element)
            print("Protected Data: %s" % protected_data)

        # Unprotect operation
        if should_unprotect:
            # Use protected data if we just protected, otherwise use input data
            data_to_unprotect = protected_data if protected_data else input_data
            org = session.unprotect(data_to_unprotect, data_element)
            print("Unprotected Data: %s" % org)

        # Encrypt operation
        if should_encrypt:
            encrypted_data = session.protect(input_data, data_element, encrypt_to=bytes)
            print("Encrypted Hex Data: %s" % encrypted_data.hex())

        # Decrypt operation
        if should_decrypt:
            # Use encrypted data if we just encrypted, otherwise assume input is hex-encoded bytes
            if encrypted_data:
                data_to_decrypt = encrypted_data
            else:
                # Convert hex string back to bytes
                data_to_decrypt = bytes.fromhex(input_data)
            decrypted_data = session.unprotect(data_to_decrypt, data_element, decrypt_to=str)
            print("Decrypted Data: %s" % decrypted_data)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
