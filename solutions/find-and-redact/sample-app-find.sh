#!/bin/sh
# Sample script to run SampleAppFind
# Discovers PII in text files using Protegrity AI Developer Edition

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
JAVA_PROJECT_DIR="$( cd "$SCRIPT_DIR/../../data-protection/samples/java" && pwd )"

JAR_FILE="$JAVA_PROJECT_DIR/target/protegrity-java-samples-1.0.0-jar-with-dependencies.jar"
MAIN_CLASS="com.protegrity.devedition.samples.SampleAppFind"

# Check if JAR exists
if [ ! -f "$JAR_FILE" ]; then
    echo "Building the project..."
    cd "$JAVA_PROJECT_DIR" && ./mvnw clean package -q
fi

echo "Running SampleAppFind..."
echo "========================================"
java -cp "$JAR_FILE" "$MAIN_CLASS" "$@"
