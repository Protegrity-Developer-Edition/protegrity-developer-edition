import { useEffect, useState } from "react";
import {
  clearTokens,
  getAccessToken,
  getCurrentUser,
  login,
  setAccessToken,
} from "../api/client";

function useAuthSession({ onLogoutCleanup } = {}) {
  const [currentUser, setCurrentUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(!!getAccessToken());
  const [authLoading, setAuthLoading] = useState(true);
  const [loginError, setLoginError] = useState(null);
  const [loginSubmitting, setLoginSubmitting] = useState(false);

  useEffect(() => {
    const bootstrapAuth = async () => {
      const token = getAccessToken();
      if (!token) {
        setIsAuthenticated(false);
        setAuthLoading(false);
        return;
      }

      try {
        const me = await getCurrentUser();
        setCurrentUser(me);
        setIsAuthenticated(true);
      } catch {
        clearTokens();
        setIsAuthenticated(false);
      } finally {
        setAuthLoading(false);
      }
    };

    bootstrapAuth();
  }, []);

  const handleLogin = async ({ username, password }) => {
    try {
      setLoginError(null);
      setLoginSubmitting(true);

      const tokens = await login({ username, password });
      setAccessToken(tokens.access);

      const me = await getCurrentUser();
      setCurrentUser(me);
      setIsAuthenticated(true);
    } catch (err) {
      setLoginError(err.message || "Login failed");
      setIsAuthenticated(false);
      clearTokens();
    } finally {
      setLoginSubmitting(false);
    }
  };

  const handleLogout = () => {
    clearTokens();
    setCurrentUser(null);
    setIsAuthenticated(false);
    setLoginError(null);

    if (onLogoutCleanup) {
      onLogoutCleanup();
    }
  };

  return {
    currentUser,
    isAuthenticated,
    authLoading,
    loginError,
    loginSubmitting,
    handleLogin,
    handleLogout,
  };
}

export default useAuthSession;
