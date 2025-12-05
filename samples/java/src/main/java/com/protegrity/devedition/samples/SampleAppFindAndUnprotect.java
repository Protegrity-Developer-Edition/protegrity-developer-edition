package com.protegrity.devedition.samples;

import com.protegrity.devedition.utils.*;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * Sample application demonstrating find and unprotect functionality.
 * 
 * This Java implementation provides equivalent functionality to the Python sample-app-find-and-unprotect.py
 * It reads protected text, discovers protected entities, unprotects them, and writes the original text to an output file.
 * 
 * Usage:
 *   java SampleAppFindAndUnprotect
 */
public class SampleAppFindAndUnprotect {
    
    private static final double DEFAULT_CLASSIFICATION_THRESHOLD = 0.6;
    private static final int SNIPPET_LENGTH = 250;
   
    public SampleAppFindAndUnprotect() {
    }
    
    /**
     * Configure the application with settings from config
     */
    public void configure(Map<String, Object> config) {
        if (config.containsKey("named_entity_map")) {
            Object entityMapObj = config.get("named_entity_map");
            if (entityMapObj instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> rawMap = (Map<String, Object>) entityMapObj;
                Map<String, String> entityMap = new HashMap<>();
                for (Map.Entry<String, Object> entry : rawMap.entrySet()) {
                    entityMap.put(entry.getKey(), String.valueOf(entry.getValue()));
                }
                // Set it in the global Config for PiiProcessing to use
                Config.setNamedEntityMap(entityMap);
            }
        }
    }
    
    /**
     * Load configuration from JSON file
     */
    public Map<String, Object> loadConfig(Path configPath) throws IOException {
        if (!Files.exists(configPath)) {
            return new HashMap<>();
        }
        
        byte[] bytes = Files.readAllBytes(configPath);
        String content = new String(bytes, StandardCharsets.UTF_8);
        return parseJson(content);
    }
    
    /**
     * Find and unprotect sensitive data in text
     */
    public String findAndUnprotect(String text) throws IOException {
        // Use PiiProcessing to unprotect the text
        try {
            return PiiProcessing.unprotectData(text);
        } catch (Exception e) {
            throw new IOException("Find and unprotect failed: " + e.getMessage(), e);
        }
    }
    
    /**
     * Process input file and write unprotected output
     */
    public void unprotectFile(Path inputPath, Path outputPath) throws IOException {
        log("INFO", "Reading from file " + inputPath + "...");
        
        // Create output directory if it doesn't exist
        Files.createDirectories(outputPath.getParent());
        
        BufferedReader reader = null;
        BufferedWriter writer = null;
        try {
            reader = Files.newBufferedReader(inputPath, StandardCharsets.UTF_8);
            writer = Files.newBufferedWriter(outputPath, StandardCharsets.UTF_8);
            
            String line;
            while ((line = reader.readLine()) != null) {
                String strippedLine = line.replaceAll("\\s+$", "");
                
                if (!strippedLine.isEmpty()) {
                    // Process non-empty lines
                    String unprotectedLine = findAndUnprotect(strippedLine);
                    writer.write(unprotectedLine);
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
        byte[] bytes = Files.readAllBytes(outputPath);
        String content = new String(bytes, StandardCharsets.UTF_8);
        String snippet = content.length() > SNIPPET_LENGTH 
            ? content.substring(0, SNIPPET_LENGTH) + "..." 
            : content;
        log("INFO", "Processed text snippet: \"" + snippet + "\"");
    }
    
    /**
     * Simple JSON parser (for production use a proper JSON library like Jackson or Gson)
     */
    private Map<String, Object> parseJson(String json) {
        Map<String, Object> result = new HashMap<>();
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
        System.out.println(timestamp + " - sample_app_find_and_unprotect - " + level + " - " + message);
    }
    
    public static void main(String[] args) {
        try {
            SampleAppFindAndUnprotect app = new SampleAppFindAndUnprotect();
            
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
            // Determine base directory (same directory as this Java file)
            Path inputFile = sampleDataDir.resolve("sample-data").resolve("output-protect.txt");
            Path outputFile = sampleDataDir.resolve("sample-data").resolve("output-unprotect.txt");
            Path configFile = sampleDataDir.resolve("config.json");
            
            // Load and apply configuration
            Map<String, Object> config = app.loadConfig(configFile);
            if (!config.isEmpty()) {
                app.configure(config);
            }
            
            // Process the file
            app.unprotectFile(inputFile, outputFile);
            
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
