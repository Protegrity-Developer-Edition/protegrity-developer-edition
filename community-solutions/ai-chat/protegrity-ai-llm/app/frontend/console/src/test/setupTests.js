import { afterEach, expect } from "vitest";
import { cleanup } from "@testing-library/react";
import * as matchers from "@testing-library/jest-dom/matchers";

// Extend Vitest's expect with all jest-dom matchers
expect.extend(matchers);

// Clean up DOM after each test
afterEach(() => {
  cleanup();
});
