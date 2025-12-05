package com.protegrity.devedition.samples;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.protegrity.devedition.utils.Config;
import com.protegrity.devedition.utils.Discover;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Sample application to discover PII in text files.
 */
public class SampleAppFind {
    
    private static final Logger logger = LoggerFactory.getLogger(SampleAppFind.class);
    private static final ObjectMapper objectMapper = new ObjectMapper();
    
    static {
        objectMapper.enable(SerializationFeature.INDENT_OUTPUT);
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
                logger.warn("Failed to load configuration from {}: {}", configPath, e.getMessage());
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
            logger.info("Reading from file {}...", inputPath);
            return new String(Files.readAllBytes(inputPath));
        } catch (IOException e) {
            logger.error("Input file not found: {}", inputPath);
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
    public static void main(String[] args) {
        try {
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
            logger.info("Found the below data...\n{}", piiOutput);
            
        } catch (Exception e) {
            logger.error("Application failed: {}", e.getMessage(), e);
            System.exit(1);
        }
    }
}
