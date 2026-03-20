import { useEffect, useRef } from "react";

/**
 * Custom hook to detect clicks outside of a ref element
 * @param {Function} callback - Function to call when click outside occurs
 * @returns {Object} ref - Ref to attach to the element
 */
function useClickOutside(callback) {
  const ref = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (ref.current && !ref.current.contains(event.target)) {
        callback();
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [callback]);

  return ref;
}

export default useClickOutside;
