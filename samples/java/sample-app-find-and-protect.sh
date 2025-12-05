#!/bin/sh
# Sample script to run SampleAppFindAndProtect
# Discovers PII and protects it in one operation

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"

JAR_FILE="$SCRIPT_DIR/target/protegrity-java-samples-1.0.0-jar-with-dependencies.jar"
MAIN_CLASS="com.protegrity.devedition.samples.SampleAppFindAndProtect"

# Check if JAR exists
if [ ! -f "$JAR_FILE" ]; then
    echo "Building the project..."
    cd "$SCRIPT_DIR" && ./mvnw clean package -q
fi

echo "Running SampleAppFindAndProtect..."
echo "========================================"
java -cp "$JAR_FILE" "$MAIN_CLASS" "$@"
