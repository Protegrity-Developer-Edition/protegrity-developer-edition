#!/bin/sh
# Sample script to run SampleAppProtection
# Demonstrates data protection operations using Protegrity Application Protector

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"

JAR_FILE="$SCRIPT_DIR/target/protegrity-java-samples-1.0.0-jar-with-dependencies.jar"
MAIN_CLASS="com.protegrity.devedition.samples.SampleAppProtection"

# Function to display usage
usage() {
    echo "Running SampleAppProtection..."
    echo "========================================"
    echo "Usage: ./sample-app-protection.sh [OPTIONS]"
    echo ""
    echo "Protect and unprotect data using Protegrity"
    echo ""
    echo "Required arguments:"
    echo "  --input_data <data>       The data to protect (e.g., 'John Smith')"
    echo "  --policy_user <user>      Policy user for the session (e.g., 'superuser')"
    echo "  --data_element <element>  Data element type (e.g., 'string', 'email')"
    echo ""
    echo "Optional arguments:"
    echo "  --protect                 Only perform protect operation"
    echo "  --unprotect               Only perform unprotect operation"
    echo "  --enc                     Only perform encrypt operation (output in hex format)"
    echo "  --dec                     Only perform decrypt operation"
    echo ""
    echo "Examples:"
    echo "  ./sample-app-protection.sh --input_data \"John Smith\" --policy_user superuser --data_element string"
    echo "  ./sample-app-protection.sh --input_data \"john@example.com\" --policy_user superuser --data_element email --protect"
    echo "  ./sample-app-protection.sh --input_data \"0QjD@example.com\" --policy_user superuser --data_element email --unprotect"
    echo "  ./sample-app-protection.sh --input_data \"John Smith\" --policy_user superuser --data_element text --enc"
    echo "  ./sample-app-protection.sh --input_data \"e7087f449913bca6471e2b3209166dbb\" --policy_user superuser --data_element text --dec"
    echo "  ./sample-app-protection.sh --input_data \"ELatin1_S+NSABC¹º»¼½¾¿ÄÅÆÇÈAlice1234567Bob\" --policy_user superuser --data_element fpe_latin1_alphanumeric --protect"
    echo "  ./sample-app-protection.sh --input_data \"VðÈuXñ5_À+Áîg1ÿ¹º»¼½¾¿12ÔP1ëÕÖlgxÏHóFÚ6O3W\" --policy_user superuser --data_element fpe_latin1_alphanumeric --unprotect"
    echo "  ./sample-app-protection.sh --input_data \"John Smith\" --policy_user hr --data_element mask --unprotect"
    echo "  ./sample-app-protection.sh --input_data \"John Smith\" --policy_user superuser --data_element no_encryption --protect"
    echo "  ./sample-app-protection.sh --input_data \"John Smith\" --policy_user superuser --data_element no_encryption --unprotect"
}

# Check if no arguments or help requested
if [ $# -eq 0 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    usage
    exit 0
fi

# Check if JAR exists
if [ ! -f "$JAR_FILE" ]; then
    echo "Building the project..."
    cd "$SCRIPT_DIR" && ./mvnw clean package -q
fi

echo "Running SampleAppProtection..."
echo "========================================"
java -cp "$JAR_FILE" "$MAIN_CLASS" "$@"
