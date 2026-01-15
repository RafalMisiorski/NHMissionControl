/**
 * NH Mission Control - Auth Provider (Real API)
 * ===============================================
 *
 * Authentication state management connected to backend.
 *
 * EPOCH 1 - Authentication (LOCKED)
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode
} from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../lib/auth-api';
import type { User, UserLogin, UserCreate } from '../types';

// ==========================================================================
// Types
// ==========================================================================

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (data: UserLogin) => Promise<void>;
  register: (data: UserCreate) => Promise<void>;
  logout: () => Promise<void>;
  updateProfile: (data: Partial<User>) => Promise<void>;
  refreshUser: () => Promise<void>;
  error: string | null;
  clearError: () => void;
}

// ==========================================================================
// Storage Keys
// ==========================================================================

const ACCESS_TOKEN_KEY = 'nh-access-token';
const REFRESH_TOKEN_KEY = 'nh-refresh-token';

// ==========================================================================
// Token Helpers (exported for API client)
// ==========================================================================

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// ==========================================================================
// Context
// ==========================================================================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ==========================================================================
// Provider Component
// ==========================================================================

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Clear error
  const clearError = useCallback(() => setError(null), []);

  // Fetch current user from API
  const refreshUser = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const userData = await authApi.getMe();
      setUser(userData);
      setError(null);
    } catch (err: unknown) {
      // Token invalid or expired - try refresh
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        try {
          const tokens = await authApi.refreshToken(refreshToken);
          setTokens(tokens.access_token, tokens.refresh_token);
          // Retry getting user
          const userData = await authApi.getMe();
          setUser(userData);
          setError(null);
          return;
        } catch {
          // Refresh failed
        }
      }

      // Clear everything
      clearTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize on mount
  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  // Login
  const login = useCallback(async (data: UserLogin) => {
    setIsLoading(true);
    setError(null);

    try {
      const tokens = await authApi.login(data);
      setTokens(tokens.access_token, tokens.refresh_token);

      const userData = await authApi.getMe();
      setUser(userData);
      navigate('/dashboard');
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const message = axiosErr.response?.data?.detail || 'Login failed';
      setError(message);
      throw new Error(message);
    } finally {
      setIsLoading(false);
    }
  }, [navigate]);

  // Register
  const register = useCallback(async (data: UserCreate) => {
    setIsLoading(true);
    setError(null);

    try {
      await authApi.register(data);
      // Auto-login after registration
      const tokens = await authApi.login({ email: data.email, password: data.password });
      setTokens(tokens.access_token, tokens.refresh_token);

      const userData = await authApi.getMe();
      setUser(userData);
      navigate('/dashboard');
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const message = axiosErr.response?.data?.detail || 'Registration failed';
      setError(message);
      throw new Error(message);
    } finally {
      setIsLoading(false);
    }
  }, [navigate]);

  // Logout
  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore logout errors
    } finally {
      clearTokens();
      setUser(null);
      setError(null);
      navigate('/login');
    }
  }, [navigate]);

  // Update profile
  const updateProfile = useCallback(async (data: Partial<User>) => {
    setError(null);

    try {
      const updatedUser = await authApi.updateMe(data);
      setUser(updatedUser);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const message = axiosErr.response?.data?.detail || 'Update failed';
      setError(message);
      throw new Error(message);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        updateProfile,
        refreshUser,
        error,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ==========================================================================
// Hook
// ==========================================================================

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
