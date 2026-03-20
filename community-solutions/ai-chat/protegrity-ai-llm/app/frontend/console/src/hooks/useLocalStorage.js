/**
 * Custom React hook for synchronized state with localStorage
 * 
 * Features:
 * - Automatic persistence to localStorage
 * - Synchronization across browser tabs
 * - Error handling and fallback to in-memory state
 * - Debounced writes to prevent excessive I/O
 * 
 * @module useLocalStorage
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { getStorageItem, setStorageItem, isStorageAvailable } from "../utils/storage";

/**
 * Hook that provides stateful value synchronized with localStorage
 * 
 * @template T
 * @param {string} key - localStorage key
 * @param {T} initialValue - Initial value if key doesn't exist
 * @param {Object} options - Configuration options
 * @param {number} options.debounceMs - Debounce time for writes (default: 500ms)
 * @param {boolean} options.syncAcrossTabs - Sync state across browser tabs (default: true)
 * @returns {[T, (value: T | ((prev: T) => T)) => void, () => void]} [value, setValue, removeValue]
 * 
 * @example
 * const [conversations, setConversations, clearConversations] = useLocalStorage('conversations', []);
 */
export function useLocalStorage(key, initialValue, options = {}) {
  const {
    debounceMs = 500,
    syncAcrossTabs = true,
  } = options;

  // Get initial value from localStorage or use initialValue
  const [storedValue, setStoredValue] = useState(() => {
    if (typeof window === "undefined") {
      return initialValue;
    }

    try {
      const item = getStorageItem(key);
      return item !== null ? item : initialValue;
    } catch (error) {
      console.error(`Error loading initial value for key "${key}":`, error);
      return initialValue;
    }
  });

  // Ref to track if we're in the middle of syncing from storage event
  const syncingRef = useRef(false);
  // Ref for debounce timeout
  const debounceTimeoutRef = useRef(null);
  // Ref to track the latest value for debounced writes
  const pendingValueRef = useRef(storedValue);

  /**
   * Write to localStorage with debouncing
   */
  const writeToStorage = useCallback(
    (value) => {
      if (!isStorageAvailable()) {
        console.warn("localStorage not available, keeping in-memory state only");
        return;
      }

      const success = setStorageItem(key, value);
      if (!success) {
        console.error(`Failed to persist value for key "${key}"`);
      }
    },
    [key]
  );

  /**
   * Debounced write function
   */
  const debouncedWrite = useCallback(
    (value) => {
      pendingValueRef.current = value;

      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }

      debounceTimeoutRef.current = setTimeout(() => {
        writeToStorage(pendingValueRef.current);
        debounceTimeoutRef.current = null;
      }, debounceMs);
    },
    [writeToStorage, debounceMs]
  );

  /**
   * Set value and persist to localStorage
   */
  const setValue = useCallback(
    (value) => {
      try {
        // Allow value to be a function for functional updates
        const valueToStore = value instanceof Function ? value(storedValue) : value;
        
        setStoredValue(valueToStore);
        
        // Debounce writes for performance
        if (debounceMs > 0) {
          debouncedWrite(valueToStore);
        } else {
          writeToStorage(valueToStore);
        }
      } catch (error) {
        console.error(`Error setting value for key "${key}":`, error);
      }
    },
    [key, storedValue, writeToStorage, debouncedWrite, debounceMs]
  );

  /**
   * Remove value from localStorage and reset to initial value
   */
  const removeValue = useCallback(() => {
    try {
      setStoredValue(initialValue);
      
      if (isStorageAvailable()) {
        localStorage.removeItem(key);
      }
      
      // Clear any pending debounced writes
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
        debounceTimeoutRef.current = null;
      }
    } catch (error) {
      console.error(`Error removing value for key "${key}":`, error);
    }
  }, [key, initialValue]);

  /**
   * Sync state across browser tabs using storage event
   */
  useEffect(() => {
    if (!syncAcrossTabs || typeof window === "undefined") {
      return;
    }

    const handleStorageChange = (e) => {
      // Check if this is our key
      if (e.key !== key) {
        return;
      }

      // Prevent infinite loops when we're the ones writing
      if (syncingRef.current) {
        return;
      }

      try {
        syncingRef.current = true;
        
        if (e.newValue === null) {
          // Key was removed
          setStoredValue(initialValue);
        } else {
          // Key was updated
          const newValue = JSON.parse(e.newValue);
          // Extract data from versioned wrapper
          const actualValue = newValue && newValue.data !== undefined 
            ? newValue.data 
            : newValue;
          setStoredValue(actualValue);
        }
      } catch (error) {
        console.error(`Error syncing storage change for key "${key}":`, error);
      } finally {
        syncingRef.current = false;
      }
    };

    window.addEventListener("storage", handleStorageChange);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
    };
  }, [key, initialValue, syncAcrossTabs]);

  /**
   * Flush any pending writes on unmount
   */
  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
        // Immediately write the pending value
        writeToStorage(pendingValueRef.current);
      }
    };
  }, [writeToStorage]);

  return [storedValue, setValue, removeValue];
}

/**
 * Specialized hook for managing conversation history with localStorage
 * Includes conversation limit and automatic cleanup
 * 
 * @param {number} maxConversations - Maximum number of conversations to keep (default: 50)
 * @returns {[Array, Function, Function, Function]} [conversations, setConversations, clearConversations, deleteConversation]
 */
export function useConversationStorage(maxConversations = 50) {
  const [conversations, setConversations, clearConversations] = useLocalStorage(
    "protegrity_ai_conversations",
    []
  );

  /**
   * Enhanced setter that enforces conversation limit
   */
  const setConversationsWithLimit = useCallback(
    (value) => {
      const newConversations = value instanceof Function ? value(conversations) : value;
      
      // Enforce maximum conversation limit
      if (newConversations.length > maxConversations) {
        // Keep the most recent conversations
        const sorted = [...newConversations].sort(
          (a, b) => new Date(b.createdAt) - new Date(a.createdAt)
        );
        setConversations(sorted.slice(0, maxConversations));
      } else {
        setConversations(newConversations);
      }
    },
    [conversations, setConversations, maxConversations]
  );

  /**
   * Delete a specific conversation by ID
   */
  const deleteConversation = useCallback(
    (conversationId) => {
      setConversations((prev) => prev.filter((conv) => conv.id !== conversationId));
    },
    [setConversations]
  );

  return [conversations, setConversationsWithLimit, clearConversations, deleteConversation];
}
