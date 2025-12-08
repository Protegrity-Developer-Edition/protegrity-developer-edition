package com.protegrity.devedition.samples;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.protegrity.devedition.utils.Config;
import com.protegrity.devedition.utils.Discover;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Sample application to discover PII in text files.
 */
public class SampleAppFind {
    
    private static Logger logger;  // Will be initialized after system properties are set
    private static final ObjectMapper objectMapper = new ObjectMapper();
    
    static {
        objectMapper.enable(SerializationFeature.INDENT_OUTPUT);
    }
    
    /**
     * Get the logger instance, creating it if necessary.
     * This is called after system properties have been set.
     */
    private static Logger getLogger() {
        if (logger == null) {
            logger = LoggerFactory.getLogger(SampleAppFind.class);
        }
        return logger;
    }
    
    /**
     * Load configuration from a JSON file if it exists.
     *
     * @param configPath Path to the configuration file
     * @return JsonNode containing configuration or null if file doesn't exist
     */
    private static JsonNode loadConfig(Path configPath) {
        if (Files.exists(configPath)) {
            try {
                return objectMapper.readTree(configPath.toFile());
            } catch (IOException e) {
                getLogger().warn("Failed to load configuration from {}: {}", configPath, e.getMessage());
            }
        }
        return null;
    }
    
    /**
     * Configure the protegrity module using the provided configuration.
     *
     * @param config JsonNode containing configuration
     */
    private static void configureProtegrity(JsonNode config) {
        if (config != null) {
            if (config.has("endpoint_url")) {
                Config.setEndpointUrl(config.get("endpoint_url").asText());
            }
            if (config.has("classification_score_threshold")) {
                Config.setClassificationScoreThreshold(
                    config.get("classification_score_threshold").asDouble()
                );
            }
            if (config.has("masking_char")) {
                Config.setMaskingChar(config.get("masking_char").asText());
            }
            if (config.has("method")) {
                Config.setMethod(config.get("method").asText());
            }
            if (config.has("enable_logging")) {
                Config.setEnableLogging(config.get("enable_logging").asBoolean());
            }
            if (config.has("log_level")) {
                Config.setLogLevel(config.get("log_level").asText());
            }
            if (config.has("named_entity_map")) {
                JsonNode entityMapNode = config.get("named_entity_map");
                if (entityMapNode.isObject()) {
                    java.util.Map<String, String> entityMap = new java.util.HashMap<>();
                    entityMapNode.fields().forEachRemaining(entry -> {
                        entityMap.put(entry.getKey(), entry.getValue().asText());
                    });
                    Config.setNamedEntityMap(entityMap);
                }
            }
        }
    }
    
    /**
     * Read and return the content of the input file.
     *
     * @param inputPath Path to the input file
     * @return Content of the file as a String
     * @throws RuntimeException if file is not found or cannot be read
     */
    private static String readInputFile(Path inputPath) {
        try {
            getLogger().info("Reading from file {}...", inputPath);
            return new String(Files.readAllBytes(inputPath));
        } catch (IOException e) {
            getLogger().error("Input file not found: {}", inputPath);
            throw new RuntimeException("Input file not found: " + inputPath, e);
        }
    }
    
    /**
     * Discover PII in the input text and return formatted JSON output.
     *
     * @param text Input text to analyze
     * @return Formatted JSON string containing discovered PII
     * @throws RuntimeException if PII discovery fails
     */
    private static String discoverPii(String text) {
        try {
            JsonNode output = Discover.discover(text);
            return objectMapper.writeValueAsString(output);
        } catch (Exception e) {
            throw new RuntimeException("PII discovery failed: " + e.getMessage(), e);
        }
    }
    
    /**
     * Main function to execute the PII discovery process.
     *
     * @param args Command line arguments
     */
    /**
     * Find config.json file by searching up the directory tree
     */
    private static Path findConfigFile() {
        Path baseDir = Paths.get(System.getProperty("user.dir"));
        Path current = baseDir;
        while (current != null) {
            Path candidate = current.resolve("samples").resolve("config.json");
            if (Files.exists(candidate)) {
                return candidate;
            }
            current = current.getParent();
        }
        return null;
    }
    
    /**
     * Configure logging before any logger classes are loaded.
     * CRITICAL: This must be called at the very start of main() before any logger classes load.
     * slf4j-simple reads system properties when logger classes are first loaded.
     */
    private static void configureLogging() {
        Path configFile = findConfigFile();
        if (configFile != null && Files.exists(configFile)) {
            try {
                // Pre-parse config to extract enable_logging and log_level WITHOUT loading any logger classes
                String configContent = new String(Files.readAllBytes(configFile), StandardCharsets.UTF_8);
                
                // Simple string parsing to avoid loading any classes that might trigger logger initialization
                boolean loggingDisabled = false;
                int enableLoggingIdx = configContent.indexOf("\"enable_logging\"");
                if (enableLoggingIdx >= 0) {
                    int colonIdx = configContent.indexOf(":", enableLoggingIdx);
                    if (colonIdx >= 0) {
                        int commaIdx = configContent.indexOf(",", colonIdx);
                        int braceIdx = configContent.indexOf("}", colonIdx);
                        int endIdx = (commaIdx >= 0 && commaIdx < braceIdx) ? commaIdx : braceIdx;
                        if (endIdx >= 0) {
                            String value = configContent.substring(colonIdx + 1, endIdx).trim();
                            loggingDisabled = value.contains("false");
                        }
                    }
                }
                
                if (loggingDisabled) {
                    System.setProperty("org.slf4j.simpleLogger.log.com.protegrity", "off");
                } else {
                    // Check for log_level
                    int logLevelIdx = configContent.indexOf("\"log_level\"");
                    if (logLevelIdx >= 0) {
                        int colonIdx = configContent.indexOf(":", logLevelIdx);
                        if (colonIdx >= 0) {
                            int startQuote = configContent.indexOf("\"", colonIdx);
                            if (startQuote >= 0) {
                                int endQuote = configContent.indexOf("\"", startQuote + 1);
                                if (endQuote >= 0) {
                                    String logLevel = configContent.substring(startQuote + 1, endQuote).toLowerCase();
                                    System.setProperty("org.slf4j.simpleLogger.log.com.protegrity", logLevel);
                                }
                            }
                        }
                    }
                }
            } catch (IOException e) {
                // Ignore config parsing errors, use defaults
            }
        }
    }
    
    public static void main(String[] args) {
        try {
            // Configure logging BEFORE any logger classes load
            configureLogging();
            
            // Get base directory - navigate up to find samples folder containing sample-data
            Path baseDir = Paths.get(System.getProperty("user.dir"));
            // Navigate up until we find the directory containing samples/sample-data folder
            Path sampleDataDir = null;
            Path current = baseDir;
            while (current != null) {
                Path candidate = current.resolve("samples").resolve("sample-data");
                if (Files.exists(candidate)) {
                    sampleDataDir = candidate.getParent();
                    break;
                }
                current = current.getParent();
            }
            if (sampleDataDir == null) {
                throw new RuntimeException("Could not find samples/sample-data directory");
            }
            Path inputFile = sampleDataDir.resolve("sample-data").resolve("input.txt");
            Path configFile = sampleDataDir.resolve("config.json");
            
            // Load and apply configuration
            JsonNode config = loadConfig(configFile);
            if (config != null) {
                configureProtegrity(config);
            }
            
            // Read input file
            String inputText = readInputFile(inputFile);
            
            // Discover PII
            String piiOutput = discoverPii(inputText);
            
            // Log the results
            getLogger().info("Found the below data...\n{}", piiOutput);
            
        } catch (Exception e) {
            getLogger().error("Application failed: {}", e.getMessage(), e);
            System.exit(1);
        }
    }
}
