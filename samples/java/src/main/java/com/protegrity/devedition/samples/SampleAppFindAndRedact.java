package com.protegrity.devedition.samples;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.databind.JsonNode;
import com.protegrity.devedition.utils.Config;
import com.protegrity.devedition.utils.Discover;
import com.protegrity.devedition.utils.PiiProcessing;

/**
 * Sample application demonstrating find and redact functionality.
 * 
 * This Java implementation provides equivalent functionality to the Python sample-app-find-and-redact.py
 * It reads input text, discovers PII entities, redacts/masks them, and writes the redacted text to an output file.
 * 
 * Usage:
 *   java SampleAppFindAndRedact
 */
public class SampleAppFindAndRedact {
    
    private static final int SNIPPET_LENGTH = 250;
    
    public SampleAppFindAndRedact() {
    }
    
    /**
     * Configure the application with settings from config
     */
    public void configure(Map<String, Object> config) {
        if (config.containsKey("endpoint_url")) {
            Config.setEndpointUrl(String.valueOf(config.get("endpoint_url")));
        }
        
        if (config.containsKey("named_entity_map")) {
            // Convert Map<String, Object> to Map<String, String>
            @SuppressWarnings("unchecked")
            Map<String, Object> entityMapObj = (Map<String, Object>) config.get("named_entity_map");
            Map<String, String> entityMap = new HashMap<String, String>();
            for (Map.Entry<String, Object> entry : entityMapObj.entrySet()) {
                entityMap.put(entry.getKey(), String.valueOf(entry.getValue()));
            }
            Config.setNamedEntityMap(entityMap);
        }
        
        if (config.containsKey("masking_char")) {
            Config.setMaskingChar(String.valueOf(config.get("masking_char")));
        }
        
        if (config.containsKey("classification_score_threshold")) {
            Object threshold = config.get("classification_score_threshold");
            if (threshold instanceof Number) {
                Config.setClassificationScoreThreshold(((Number) threshold).doubleValue());
            } else {
                Config.setClassificationScoreThreshold(Double.parseDouble(String.valueOf(threshold)));
            }
        }
        
        if (config.containsKey("method")) {
            Config.setMethod(String.valueOf(config.get("method")));
        }
        
        if (config.containsKey("enable_logging")) {
            Object enableLogging = config.get("enable_logging");
            if (enableLogging instanceof Boolean) {
                Config.setEnableLogging((Boolean) enableLogging);
            } else {
                Config.setEnableLogging(Boolean.parseBoolean(String.valueOf(enableLogging)));
            }
        }
        
        if (config.containsKey("log_level")) {
            Config.setLogLevel(String.valueOf(config.get("log_level")));
        }
    }
    
    /**
     * Load configuration from JSON file
     */
    public Map<String, Object> loadConfig(Path configPath) throws IOException {
        if (!Files.exists(configPath)) {
            return new HashMap<String, Object>();
        }
        
        String content = new String(Files.readAllBytes(configPath), StandardCharsets.UTF_8);
        return parseJson(content);
    }
    
    /**
     * Find and redact sensitive data in text
     */
    public String findAndRedact(String text) throws IOException {
        // Use Discover API to find PII, then redact it
        try {
            JsonNode discoveryResult = Discover.discover(text);
            List<PiiProcessing.EntitySpan> entities = PiiProcessing.collectEntitySpans(discoveryResult, text);
            return PiiProcessing.redactData(entities, text);
        } catch (Exception e) {
            throw new IOException("Find and redact failed: " + e.getMessage(), e);
        }
    }
    
    /**
     * Process input file and write redacted output
     */
    public void redactFile(Path inputPath, Path outputPath) throws IOException {
        log("INFO", "Reading from file " + inputPath + "...");
        
        // Create output directory if it doesn't exist
        Files.createDirectories(outputPath.getParent());
        
        BufferedReader reader = null;
        BufferedWriter writer = null;
        try {
            reader = new BufferedReader(
                new InputStreamReader(new FileInputStream(inputPath.toFile()), StandardCharsets.UTF_8));
            writer = new BufferedWriter(
                new OutputStreamWriter(new FileOutputStream(outputPath.toFile()), StandardCharsets.UTF_8));
            
            String line;
            while ((line = reader.readLine()) != null) {
                String strippedLine = line.replaceAll("\\s+$", "");
                
                if (!strippedLine.isEmpty()) {
                    // Process non-empty lines
                    String redactedLine = findAndRedact(strippedLine);
                    writer.write(redactedLine);
                    writer.newLine();
                } else {
                    // Keep empty lines as is
                    writer.newLine();
                }
            }
        } finally {
            if (reader != null) {
                try { reader.close(); } catch (IOException e) { /* ignore */ }
            }
            if (writer != null) {
                try { writer.close(); } catch (IOException e) { /* ignore */ }
            }
        }
        
        log("INFO", "Processed text written to: " + outputPath);
    }
    
    /**
     * Log a snippet of the output file
     */
    public void logOutputSnippet(Path outputPath) throws IOException {
        String content = new String(Files.readAllBytes(outputPath), StandardCharsets.UTF_8);
        String snippet = content.length() > SNIPPET_LENGTH 
            ? content.substring(0, SNIPPET_LENGTH) + "..." 
            : content;
        log("INFO", "Processed text snippet: \"" + snippet + "\"");
    }
    
    /**
     * Simple JSON parser (for production use a proper JSON library like Jackson or Gson)
     */
    private Map<String, Object> parseJson(String json) {
        Map<String, Object> result = new HashMap<String, Object>();
        json = json.trim();
        
        if (!json.startsWith("{") || !json.endsWith("}")) {
            return result;
        }
        
        json = json.substring(1, json.length() - 1).trim();
        
        // Simple parser for key-value pairs
        int i = 0;
        while (i < json.length()) {
            // Skip whitespace
            while (i < json.length() && Character.isWhitespace(json.charAt(i))) {
                i++;
            }
            
            if (i >= json.length()) break;
            
            // Parse key
            if (json.charAt(i) != '"') break;
            i++; // skip opening quote
            
            int keyStart = i;
            while (i < json.length() && json.charAt(i) != '"') {
                if (json.charAt(i) == '\\') i++; // skip escaped char
                i++;
            }
            String key = json.substring(keyStart, i);
            i++; // skip closing quote
            
            // Skip to colon
            while (i < json.length() && json.charAt(i) != ':') {
                i++;
            }
            i++; // skip colon
            
            // Skip whitespace
            while (i < json.length() && Character.isWhitespace(json.charAt(i))) {
                i++;
            }
            
            // Parse value
            Object value = null;
            if (i < json.length()) {
                if (json.charAt(i) == '"') {
                    // String value
                    i++; // skip opening quote
                    int valueStart = i;
                    while (i < json.length() && json.charAt(i) != '"') {
                        if (json.charAt(i) == '\\') i++;
                        i++;
                    }
                    value = json.substring(valueStart, i);
                    i++; // skip closing quote
                } else if (json.charAt(i) == '{') {
                    // Object value - find matching closing brace
                    int braceCount = 1;
                    int objStart = i;
                    i++;
                    while (i < json.length() && braceCount > 0) {
                        if (json.charAt(i) == '{') braceCount++;
                        else if (json.charAt(i) == '}') braceCount--;
                        i++;
                    }
                    String objJson = json.substring(objStart, i);
                    value = parseJson(objJson);
                } else if (Character.isDigit(json.charAt(i)) || json.charAt(i) == '-') {
                    // Number value
                    int valueStart = i;
                    while (i < json.length() && (Character.isDigit(json.charAt(i)) || json.charAt(i) == '.' || json.charAt(i) == '-')) {
                        i++;
                    }
                    String numStr = json.substring(valueStart, i);
                    try {
                        if (numStr.contains(".")) {
                            value = Double.parseDouble(numStr);
                        } else {
                            value = Integer.parseInt(numStr);
                        }
                    } catch (NumberFormatException e) {
                        value = numStr;
                    }
                } else if (json.startsWith("true", i)) {
                    value = true;
                    i += 4;
                } else if (json.startsWith("false", i)) {
                    value = false;
                    i += 5;
                } else if (json.startsWith("null", i)) {
                    value = null;
                    i += 4;
                }
            }
            
            result.put(key, value);
            
            // Skip to next entry
            while (i < json.length() && json.charAt(i) != ',' && json.charAt(i) != '}') {
                i++;
            }
            if (i < json.length() && json.charAt(i) == ',') {
                i++; // skip comma
            }
        }
        
        return result;
    }
    
    /**
     * Simple logging
     */
    private void log(String level, String message) {
        String timestamp = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss,SSS").format(new Date());
        System.out.println(timestamp + " - sample_app_find_and_redact - " + level + " - " + message);
    }
    
    /**
     * Find config.json file by searching up the directory tree.
     */
    private static Path findConfigFile() {
        try {
            Path baseDir = Paths.get(System.getProperty("user.dir"));
            Path current = baseDir;
            while (current != null) {
                Path candidate = current.resolve("samples").resolve("config.json");
                if (Files.exists(candidate)) {
                    return candidate;
                }
                current = current.getParent();
            }
        } catch (Exception e) {
            // Ignore
        }
        return null;
    }
    
    /**
     * Configure logging before any logger classes are loaded.
     * CRITICAL: This must be called at the very start of main() before creating any objects.
     * slf4j-simple reads system properties when logger classes are first loaded.
     */
    private static void configureLogging() {
        Path configFile = findConfigFile();
        if (configFile != null && Files.exists(configFile)) {
            try {
                String content = new String(Files.readAllBytes(configFile), StandardCharsets.UTF_8);
                // Quick parse for log_level and enable_logging only
                if (content.contains("\"enable_logging\"") && content.contains("false")) {
                    System.setProperty("org.slf4j.simpleLogger.log.com.protegrity", "off");
                } else if (content.contains("\"log_level\"")) {
                    // Extract log_level value with simple string parsing
                    int logLevelPos = content.indexOf("\"log_level\"");
                    int colonPos = content.indexOf(":", logLevelPos);
                    int quoteStart = content.indexOf("\"", colonPos + 1);
                    int quoteEnd = content.indexOf("\"", quoteStart + 1);
                    if (quoteStart > 0 && quoteEnd > quoteStart) {
                        String logLevel = content.substring(quoteStart + 1, quoteEnd).toLowerCase();
                        System.setProperty("org.slf4j.simpleLogger.log.com.protegrity", logLevel);
                    }
                }
            } catch (IOException e) {
                // Ignore config parsing errors, use defaults
            }
        }
    }
    
    public static void main(String[] args) {
        try {
            // Configure logging BEFORE creating any objects
            configureLogging();
            
            SampleAppFindAndRedact app = new SampleAppFindAndRedact();
            
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
            Path outputFile = sampleDataDir.resolve("sample-data").resolve("output-redact.txt");
            Path configFile = sampleDataDir.resolve("config.json");
            
            // Load and apply configuration
            Map<String, Object> config = app.loadConfig(configFile);
            
            // Now apply the rest of the configuration
            if (!config.isEmpty()) {
                app.log("INFO", "Loading configuration from: " + configFile);
                app.configure(config);
                app.log("INFO", "Config applied - method: " + Config.getMethod() + 
                       ", masking_char: " + Config.getMaskingChar() +
                       ", threshold: " + Config.getClassificationScoreThreshold() +
                       ", endpoint: " + Config.getEndpointUrl() +
                       ", enable_logging: " + Config.isEnableLogging() +
                       ", log_level: " + Config.getLogLevel());
            }
            
            // Process the file
            app.redactFile(inputFile, outputFile);
            
            // Log snippet of output
            app.logOutputSnippet(outputFile);
            
        } catch (FileNotFoundException e) {
            System.err.println("Error: File not found: " + e.getMessage());
            System.exit(1);
        } catch (IOException e) {
            System.err.println("Error: I/O error: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
}
