# Protegrity AI Developer Edition - Java Samples

Sample applications demonstrating how to use Protegrity's Application Protector Java SDK and Developer Edition utilities for data discovery and protection.

## Prerequisites

- Java 8 or later
- Maven 3.6+ (or use the included Maven wrapper `./mvnw`)
- Protegrity AI Developer Edition credentials:
  - `DEV_EDITION_EMAIL`
  - `DEV_EDITION_PASSWORD`
  - `DEV_EDITION_API_KEY`

## Quick Start

### 1. Set Environment Variables

```bash
export DEV_EDITION_EMAIL="your-email@example.com"
export DEV_EDITION_PASSWORD="your-password"
export DEV_EDITION_API_KEY="your-api-key"
```

### 2. Build the Project

```bash
# Using Maven wrapper (recommended)
./mvnw clean package

# Or using system Maven
mvn clean package
```

This creates a fat JAR with all dependencies:
- `target/protegrity-java-samples-1.0.0-jar-with-dependencies.jar` (4.4 MB)

### 3. Run the Samples

#### Option 1: Using Shell Scripts (Easiest)

```bash
# Discover PII in text
./sample-app-find.sh

# Protect data
./sample-app-protection.sh

# Find and protect in one operation
./sample-app-find-and-protect.sh

# Find and unprotect
./sample-app-find-and-unprotect.sh

# Find and redact
./sample-app-find-and-redact.sh
```

#### Option 2: Using Java Directly

```bash
# Run with default main class
java -jar target/protegrity-java-samples-1.0.0-jar-with-dependencies.jar

# Run specific sample
java -cp target/protegrity-java-samples-1.0.0-jar-with-dependencies.jar \
  com.protegrity.devedition.samples.SampleAppFind

java -cp target/protegrity-java-samples-1.0.0-jar-with-dependencies.jar \
  com.protegrity.devedition.samples.SampleAppProtection

java -cp target/protegrity-java-samples-1.0.0-jar-with-dependencies.jar \
  com.protegrity.devedition.samples.SampleAppFindAndProtect

java -cp target/protegrity-java-samples-1.0.0-jar-with-dependencies.jar \
  com.protegrity.devedition.samples.SampleAppFindAndUnprotect

java -cp target/protegrity-java-samples-1.0.0-jar-with-dependencies.jar \
  com.protegrity.devedition.samples.SampleAppFindAndRedact
```

## Sample Descriptions

### 1. SampleAppFind
Discovers Personally Identifiable Information (PII) in text using Protegrity's data discovery capabilities.

**Features:**
- Detects SSN, credit cards, email addresses, phone numbers
- Works with text files
- Returns entity types and positions

**Usage:**
```bash
./sample-app-find.sh
```

### 2. SampleAppProtection
Demonstrates basic data protection operations using Application Protector Java SDK.

**Features:**
- Protect sensitive data
- Unprotect data
- Reprotect data with different data elements
- Supports various data types (strings, integers, bytes)

**Usage:**
```bash
./sample-app-protection.sh
```

### 3. SampleAppFindAndProtect
Combines data discovery and protection in a single workflow.

**Features:**
- Discovers PII in text
- Automatically protects discovered entities
- Preserves text structure

**Usage:**
```bash
./sample-app-find-and-protect.sh
```

### 4. SampleAppFindAndUnprotect
Discovers protected data and unprotects it.

**Features:**
- Identifies protected data in text
- Unprotects discovered protected values
- Handles multiple data elements

**Usage:**
```bash
./sample-app-find-and-unprotect.sh
```

### 5. SampleAppFindAndRedact
Discovers PII and redacts it for privacy compliance.

**Features:**
- Detects sensitive information
- Replaces with redaction patterns (e.g., `***-**-1234`)
- Maintains text readability

**Usage:**
```bash
./sample-app-find-and-redact.sh
```

## Project Structure

```
samples/java/
├── pom.xml                                    # Maven configuration
├── mvnw, mvnw.cmd                            # Maven wrapper scripts
├── sample-app-*.sh                           # Sample execution scripts
├── src/main/java/com/protegrity/devedition/samples/
│   ├── SampleAppFind.java
│   ├── SampleAppProtection.java
│   ├── SampleAppFindAndProtect.java
│   ├── SampleAppFindAndUnprotect.java
│   └── SampleAppFindAndRedact.java
└── target/
    └── protegrity-java-samples-1.0.0-jar-with-dependencies.jar
```

## Dependencies

The project uses:
- **Application Protector Java** (`com.protegrity:application-protector-java:1.0.1`)
  - Core data protection SDK
- **Protegrity Developer Edition** (`com.protegrity:protegrity-developer-edition:1.0.1`)
  - Data discovery and advanced utilities
- **Jackson** - JSON processing
- **SLF4J/Logback** - Logging
- **Apache HttpClient** - HTTP operations

## Configuration

Samples can be configured via:

1. **Environment Variables** (recommended):
   ```bash
   export DEV_EDITION_EMAIL="..."
   export DEV_EDITION_PASSWORD="..."
   export DEV_EDITION_API_KEY="..."
   ```

2. **Configuration File** (optional):
   Create `config.json` with sample-specific settings

## Troubleshooting

### Build Issues

```bash
# Clean build
./mvnw clean package

# Force update dependencies
./mvnw clean package -U

# Skip tests
./mvnw clean package -DskipTests
```

### Runtime Issues

**Missing credentials:**
```
Error: DEV_EDITION_EMAIL environment variable not set
```
Solution: Set all three required environment variables

**Connection timeout:**
```
Error: Connection timeout
```
Solution: Check network connectivity and API endpoint configuration

**Invalid API key:**
```
Error: Authentication failed
```
Solution: Verify API key is correct and active

## Additional Resources

- [Protegrity Developer Portal](https://www.protegrity.com/developers)
- [Documentation](http://developer.docs.protegrity.com)
- [GitHub Repository](https://github.com/Protegrity-Developer-Edition/protegrity-developer-java)

## Support

For issues or questions:
- Email: info@protegrity.com
- Documentation: http://developer.docs.protegrity.com

## License

MIT License - See [LICENSE](../../LICENSE) file for details
