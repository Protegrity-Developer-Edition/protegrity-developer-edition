package com.protegrity.devedition.samples;

import com.protegrity.ap.java.Protector;
import com.protegrity.ap.java.ProtectorException;
import com.protegrity.ap.java.SessionObject;
import com.protegrity.ap.java.SessionTimeoutException;

/**
 * Sample application demonstrating data protection and unprotection using Protegrity Protector library.
 * 
 * Usage examples:
 *   java SampleAppProtection --input_data "John Smith" --policy_user superuser --data_element string
 *   java SampleAppProtection --input_data "john@example.com" --policy_user superuser --data_element email --protect
 *   java SampleAppProtection --input_data "0QjD@example.com" --policy_user superuser --data_element email --unprotect
 *   java SampleAppProtection --input_data "John Smith" --policy_user superuser --data_element text --enc
 *   java SampleAppProtection --input_data "e7087f449913bca6471e2b3209166dbb" --policy_user superuser --data_element string --dec
 *   java SampleAppProtection --input_data "ELatin1_S+NSABC¹º»¼½¾¿ÄÅÆÇÈAlice1234567Bob" --policy_user superuser --data_element fpe_latin1_alphanumeric --protect
 *   java SampleAppProtection --input_data "VðÈuXñ5_À+Áîg1ÿ¹º»¼½¾¿12ÔP1ëÕÖlgxÏHóFÚ6O3W" --policy_user superuser --data_element fpe_latin1_alphanumeric --unprotect
 *   java SampleAppProtection --input_data "John Smith" --policy_user hr --data_element mask --unprotect
 *   java SampleAppProtection --input_data "John Smith" --policy_user superuser --data_element no_encryption --protect
 *   java SampleAppProtection --input_data "John Smith" --policy_user superuser --data_element no_encryption --unprotect
 */  
 

public class SampleAppProtection {
    
    private final Protector protector;
    private final SessionObject session;
    
    public SampleAppProtection(String policyUser) throws ProtectorException {
        this.protector = Protector.getProtector();
        this.session = protector.createSession(policyUser);
    }
    
    /**
     * Protect data using the specified data element
     */
    public String protect(String data, String dataElement) throws ProtectorException, SessionTimeoutException {
        String[] input = {data};
        String[] output = new String[1];
        
        protector.protect(session, dataElement, input, output);
        
        return output[0];
    }
    
    /**
     * Protect data and return as encrypted bytes in hex format
     */
    public String protectToHex(String data, String dataElement) throws ProtectorException, SessionTimeoutException {
        String[] input = {data};
        byte[][] output = new byte[1][];
        
        protector.protect(session, dataElement, input, output);
        
        return bytesToHex(output[0]);
    }
    
    /**
     * Unprotect data using the specified data element
     */
    public String unprotect(String data, String dataElement) throws ProtectorException, SessionTimeoutException {
        String[] input = {data};
        String[] output = new String[1];
        
        protector.unprotect(session, dataElement, input, output);
        
        return output[0];
    }
    
    /**
     * Decrypt hex-encoded encrypted data
     */
    public String decryptFromHex(String hexData, String dataElement) throws ProtectorException, SessionTimeoutException {
        byte[] bytes = hexToBytes(hexData);
        byte[][] input = {bytes};
        String[] output = new String[1];
        
        protector.unprotect(session, dataElement, input, output);
        
        return output[0];
    }
    
    /**
     * Convert bytes to hex string
     */
    private String bytesToHex(byte[] bytes) {
        StringBuilder hexString = new StringBuilder();
        for (byte b : bytes) {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1) {
                hexString.append('0');
            }
            hexString.append(hex);
        }
        return hexString.toString();
    }
    
    /**
     * Convert hex string to bytes
     */
    private byte[] hexToBytes(String hex) {
        int len = hex.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            data[i / 2] = (byte) ((Character.digit(hex.charAt(i), 16) << 4)
                                + Character.digit(hex.charAt(i + 1), 16));
        }
        return data;
    }
    
    /**
     * Print usage information
     */
    private static void printUsage() {
        System.out.println("Usage: java SampleAppProtection [OPTIONS]");
        System.out.println();
        System.out.println("Protect and unprotect data using Protegrity");
        System.out.println();
        System.out.println("Required arguments:");
        System.out.println("  --input_data <data>       The data to protect (e.g., 'John Smith')");
        System.out.println("  --policy_user <user>      Policy user for the session (e.g., 'superuser')");
        System.out.println("  --data_element <element>  Data element type (e.g., 'string', 'email')");
        System.out.println();
        System.out.println("Optional arguments:");
        System.out.println("  --protect                 Only perform protect operation");
        System.out.println("  --unprotect               Only perform unprotect operation");
        System.out.println("  --enc                     Only perform encrypt operation (output in hex format)");
        System.out.println("  --dec                     Only perform decrypt operation");
        System.out.println();
        System.out.println("Examples:");
        System.out.println("  java SampleAppProtection --input_data \"John Smith\" --policy_user superuser --data_element string");
        System.out.println("  java SampleAppProtection --input_data \"john@example.com\" --policy_user superuser --data_element email --protect");
        System.out.println("  java SampleAppProtection --input_data \"0QjD@example.com\" --policy_user superuser --data_element email --unprotect");
        System.out.println("  java SampleAppProtection --input_data \"John Smith\" --policy_user superuser --data_element text --enc");
        System.out.println("  java SampleAppProtection --input_data \"e7087f449913bca6471e2b3209166dbb\" --policy_user superuser --data_element text --dec");
        System.out.println("  java SampleAppProtection --input_data \"ELatin1_S+NSABC¹º»¼½¾¿ÄÅÆÇÈAlice1234567Bob\" --policy_user superuser --data_element fpe_latin1_alphanumeric --protect");
        System.out.println("  java SampleAppProtection --input_data \"VðÈuXñ5_À+Áîg1ÿ¹º»¼½¾¿12ÔP1ëÕÖlgxÏHóFÚ6O3W\" --policy_user superuser --data_element fpe_latin1_alphanumeric --unprotect");
        System.out.println("  java SampleAppProtection --input_data \"John Smith\" --policy_user hr --data_element mask --unprotect");
        System.out.println("  java SampleAppProtection --input_data \"John Smith\" --policy_user superuser --data_element no_encryption --protect");
        System.out.println("  java SampleAppProtection --input_data \"John Smith\" --policy_user superuser --data_element no_encryption --unprotect");
    }
    
    public static void main(String[] args) {
        // Check if no arguments provided
        if (args.length == 0) {
            printUsage();
            System.exit(1);
        }
        
        // Parse command line arguments
        String inputData = null;
        String policyUser = null;
        String dataElement = null;
        boolean protectOnly = false;
        boolean unprotectOnly = false;
        boolean encryptOnly = false;
        boolean decryptOnly = false;
        
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--input_data":
                    if (i + 1 < args.length) {
                        inputData = args[++i];
                    }
                    break;
                case "--policy_user":
                    if (i + 1 < args.length) {
                        policyUser = args[++i];
                    }
                    break;
                case "--data_element":
                    if (i + 1 < args.length) {
                        dataElement = args[++i];
                    }
                    break;
                case "--protect":
                    protectOnly = true;
                    break;
                case "--unprotect":
                    unprotectOnly = true;
                    break;
                case "--enc":
                    encryptOnly = true;
                    break;
                case "--dec":
                    decryptOnly = true;
                    break;
                case "--help":
                case "-h":
                    printUsage();
                    System.exit(0);
                    break;
                default:
                    System.err.println("Unknown argument: " + args[i]);
                    printUsage();
                    System.exit(1);
            }
        }
        
        // Validate required arguments
        if (inputData == null || policyUser == null || dataElement == null) {
            System.err.println("Error: Missing required arguments");
            printUsage();
            System.exit(1);
        }
        
        // Determine which operations to perform
        boolean shouldProtect = protectOnly || (!protectOnly && !unprotectOnly && !encryptOnly && !decryptOnly);
        boolean shouldUnprotect = unprotectOnly || (!protectOnly && !unprotectOnly && !encryptOnly && !decryptOnly);
        boolean shouldEncrypt = encryptOnly;
        boolean shouldDecrypt = decryptOnly;
        
        try {
            SampleAppProtection app = new SampleAppProtection(policyUser);
            
            String protectedData = null;
            String encryptedHex = null;
            
            // Protect operation
            if (shouldProtect) {
                protectedData = app.protect(inputData, dataElement);
                System.out.println("Protected Data: " + protectedData);
            }
            
            // Unprotect operation
            if (shouldUnprotect) {
                String dataToUnprotect = (protectedData != null) ? protectedData : inputData;
                String originalData = app.unprotect(dataToUnprotect, dataElement);
                System.out.println("Unprotected Data: " + originalData);
            }
            
            // Encrypt operation
            if (shouldEncrypt) {
                encryptedHex = app.protectToHex(inputData, dataElement);
                System.out.println("Encrypted Hex Data: " + encryptedHex);
            }
            
            // Decrypt operation
            if (shouldDecrypt) {
                String hexToDecrypt = (encryptedHex != null) ? encryptedHex : inputData;
                String decryptedData = app.decryptFromHex(hexToDecrypt, dataElement);
                System.out.println("Decrypted Data: " + decryptedData);
            }
            
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
}
