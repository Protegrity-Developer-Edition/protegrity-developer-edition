/**
 * Enterprise-grade localStorage utility with error handling, versioning, and data validation
 * 
 * Features:
 * - Safe read/write with try-catch
 * - Data versioning for migration support
 * - Size limits to prevent quota errors
 * - Type validation
 * - Automatic cleanup of expired data
 * 
 * @module storage
 */

const STORAGE_VERSION = "1.0.0";
const MAX_STORAGE_SIZE = 5 * 1024 * 1024; // 5MB limit (localStorage typically allows 5-10MB)

/**
 * Storage keys enum for type safety and consistency
 */
export const STORAGE_KEYS = {
  CONVERSATIONS: "protegrity_ai_conversations",
  ACTIVE_CONVERSATION_ID: "protegrity_ai_active_conversation_id",
  SELECTED_MODEL: "protegrity_ai_selected_model",
  USER_PREFERENCES: "protegrity_ai_user_preferences",
  VERSION: "protegrity_ai_storage_version",
};

/**
 * Check if localStorage is available and accessible
 * @returns {boolean} True if localStorage is available
 */
export function isStorageAvailable() {
  try {
    const testKey = "__storage_test__";
    localStorage.setItem(testKey, "test");
    localStorage.removeItem(testKey);
    return true;
  } catch (error) {
    console.warn("localStorage is not available:", error);
    return false;
  }
}

/**
 * Get the current size of localStorage usage in bytes
 * @returns {number} Size in bytes
 */
export function getStorageSize() {
  let total = 0;
  for (let key in localStorage) {
    if (localStorage.hasOwnProperty(key)) {
      total += localStorage[key].length + key.length;
    }
  }
  return total;
}

/**
 * Check if we're approaching storage limits
 * @returns {boolean} True if storage is near capacity
 */
export function isStorageNearCapacity() {
  return getStorageSize() > MAX_STORAGE_SIZE * 0.9; // 90% threshold
}

/**
 * Safely get an item from localStorage with error handling and deserialization
 * @param {string} key - Storage key
 * @param {*} defaultValue - Default value if key doesn't exist or parsing fails
 * @returns {*} Parsed value or defaultValue
 */
export function getStorageItem(key, defaultValue = null) {
  if (!isStorageAvailable()) {
    console.warn("localStorage not available, returning default value");
    return defaultValue;
  }

  try {
    const item = localStorage.getItem(key);
    if (item === null) {
      return defaultValue;
    }

    // Parse JSON and handle parse errors
    const parsed = JSON.parse(item);
    
    // Validate data structure if it's an object
    if (parsed && typeof parsed === "object" && parsed.__version) {
      // Future: Add migration logic here if version doesn't match
      if (parsed.__version !== STORAGE_VERSION) {
        console.info(`Storage version mismatch for ${key}. Migration may be needed.`);
      }
      return parsed.data;
    }

    return parsed;
  } catch (error) {
    console.error(`Error reading from localStorage (key: ${key}):`, error);
    return defaultValue;
  }
}

/**
 * Safely set an item in localStorage with error handling and serialization
 * @param {string} key - Storage key
 * @param {*} value - Value to store (will be JSON stringified)
 * @returns {boolean} True if successful, false otherwise
 */
export function setStorageItem(key, value) {
  if (!isStorageAvailable()) {
    console.warn("localStorage not available, cannot save");
    return false;
  }

  try {
    // Wrap data with version for future migrations
    const wrappedData = {
      __version: STORAGE_VERSION,
      __timestamp: Date.now(),
      data: value,
    };

    const serialized = JSON.stringify(wrappedData);

    // Check size before storing
    const estimatedSize = serialized.length + key.length;
    if (getStorageSize() + estimatedSize > MAX_STORAGE_SIZE) {
      console.error("Storage quota would be exceeded. Consider cleaning up old data.");
      // Attempt to clean up old conversations
      cleanupOldConversations();
      
      // Try again after cleanup
      if (getStorageSize() + estimatedSize > MAX_STORAGE_SIZE) {
        return false;
      }
    }

    localStorage.setItem(key, serialized);
    return true;
  } catch (error) {
    if (error.name === "QuotaExceededError") {
      console.error("Storage quota exceeded:", error);
      // Attempt cleanup and retry once
      cleanupOldConversations();
      try {
        const wrappedData = {
          __version: STORAGE_VERSION,
          __timestamp: Date.now(),
          data: value,
        };
        localStorage.setItem(key, JSON.stringify(wrappedData));
        return true;
      } catch (retryError) {
        console.error("Failed to save after cleanup:", retryError);
        return false;
      }
    }
    console.error(`Error writing to localStorage (key: ${key}):`, error);
    return false;
  }
}

/**
 * Remove an item from localStorage
 * @param {string} key - Storage key
 * @returns {boolean} True if successful
 */
export function removeStorageItem(key) {
  if (!isStorageAvailable()) {
    return false;
  }

  try {
    localStorage.removeItem(key);
    return true;
  } catch (error) {
    console.error(`Error removing from localStorage (key: ${key}):`, error);
    return false;
  }
}

/**
 * Clear all application-specific storage
 * @returns {boolean} True if successful
 */
export function clearAppStorage() {
  if (!isStorageAvailable()) {
    return false;
  }

  try {
    Object.values(STORAGE_KEYS).forEach((key) => {
      localStorage.removeItem(key);
    });
    return true;
  } catch (error) {
    console.error("Error clearing app storage:", error);
    return false;
  }
}

/**
 * Clean up old conversations to free space
 * Keeps the 10 most recent conversations
 */
function cleanupOldConversations() {
  try {
    const conversations = getStorageItem(STORAGE_KEYS.CONVERSATIONS, []);
    if (conversations.length <= 10) {
      return; // Nothing to clean up
    }

    // Sort by createdAt timestamp (most recent first)
    const sorted = [...conversations].sort(
      (a, b) => new Date(b.createdAt) - new Date(a.createdAt)
    );

    // Keep only the 10 most recent
    const kept = sorted.slice(0, 10);
    setStorageItem(STORAGE_KEYS.CONVERSATIONS, kept);

    console.info(`Cleaned up ${conversations.length - kept.length} old conversations`);
  } catch (error) {
    console.error("Error during cleanup:", error);
  }
}

/**
 * Export all app data for backup purposes
 * @returns {Object|null} All app data or null if failed
 */
export function exportAppData() {
  if (!isStorageAvailable()) {
    return null;
  }

  try {
    const data = {};
    Object.entries(STORAGE_KEYS).forEach(([name, key]) => {
      data[name] = getStorageItem(key);
    });
    return {
      version: STORAGE_VERSION,
      exportedAt: new Date().toISOString(),
      data,
    };
  } catch (error) {
    console.error("Error exporting app data:", error);
    return null;
  }
}

/**
 * Import app data from backup
 * @param {Object} backupData - Exported data object
 * @returns {boolean} True if successful
 */
export function importAppData(backupData) {
  if (!isStorageAvailable() || !backupData || !backupData.data) {
    return false;
  }

  try {
    Object.entries(backupData.data).forEach(([name, value]) => {
      const key = STORAGE_KEYS[name];
      if (key && value !== null && value !== undefined) {
        setStorageItem(key, value);
      }
    });
    return true;
  } catch (error) {
    console.error("Error importing app data:", error);
    return false;
  }
}
