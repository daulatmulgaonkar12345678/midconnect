'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { 
  User,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  sendEmailVerification,
  sendPasswordResetEmail
} from 'firebase/auth';
import { auth } from '@/lib/firebase';
import { getUserProfile, registerUser, ApiError, warmBackend } from '@/lib/api';
import type { UserProfile } from '@/types';

// User roles for role-based access control
export type UserRole = 'guest' | 'buyer' | 'seller' | 'admin';

// Registration state for users who have Firebase account but no backend profile
export type RegistrationState = 'complete' | 'incomplete' | 'unknown';

// Connection state for server warm-up
export type ConnectionState = 'connecting' | 'ready' | 'error';

interface AuthState {
  user: User | null;
  profile: UserProfile | null;
  loading: boolean;
  error: string | null;
  registrationState: RegistrationState;
  connectionState: ConnectionState;
  connectionMessage: string;
}

interface AuthContextType extends AuthState {
  // Computed properties
  isAuthenticated: boolean;
  isAdmin: boolean;
  isSeller: boolean;
  role: UserRole;
  needsRegistration: boolean;
  
  // Auth actions
  signIn: (email: string, password: string) => Promise<{ needsRegistration: boolean }>;
  signUp: (email: string, password: string, profileData: {
    businessName: string;
    phone: string;
    city: string;
    state: string;
    pincode: string;
  }) => Promise<void>;
  completeRegistration: (profileData: {
    businessName: string;
    phone: string;
    city: string;
    state: string;
    pincode: string;
  }) => Promise<void>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  
  // Token management
  getIdToken: () => Promise<string | null>;
  
  // Profile management
  refreshProfile: () => Promise<void>;
  
  // Error handling
  clearError: () => void;
  
  // Connection state
  connectionState: ConnectionState;
  connectionMessage: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    profile: null,
    loading: true,
    error: null,
    registrationState: 'unknown',
    connectionState: 'connecting',
    connectionMessage: 'Connecting to server...',
  });

  // Warm backend before making auth calls
  const warmupBackend = useCallback(async () => {
    setState(prev => ({ 
      ...prev, 
      connectionState: 'connecting',
      connectionMessage: 'Connecting to server...'
    }));
    
    const result = await warmBackend();
    
    setState(prev => ({ 
      ...prev, 
      connectionState: result.ready ? 'ready' : 'connecting',
      connectionMessage: result.message
    }));
    
    return result.ready;
  }, []);

  // Fetch profile helper - never logs tokens
  // Returns null if user not found (404) - this means registration is incomplete
  const fetchProfile = useCallback(async (user: User): Promise<UserProfile | null> => {
    try {
      const token = await user.getIdToken();
      return await getUserProfile(token);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        // User exists in Firebase but not registered in backend
        // This is NOT an error - user needs to complete registration
        return null;
      }
      if (error instanceof ApiError && error.status === 401) {
        // Token invalid/expired - not a profile issue
        return null;
      }
      throw error;
    }
  }, []);

  // Initialize auth state listener
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        try {
          // Warm backend before fetching profile
          await warmupBackend();
          
          const profile = await fetchProfile(user);
          setState(prev => ({
            ...prev,
            user,
            profile,
            loading: false,
            error: null,
            registrationState: profile ? 'complete' : 'incomplete',
            connectionState: 'ready',
            connectionMessage: 'Connected',
          }));
        } catch (error) {
          // Unexpected error - don't expose details
          setState(prev => ({
            ...prev,
            user,
            profile: null,
            loading: false,
            error: 'Failed to load profile. Please try again.',
            registrationState: 'unknown',
            connectionState: 'error',
            connectionMessage: 'Connection error',
          }));
        }
      } else {
        setState(prev => ({
          ...prev,
          user: null,
          profile: null,
          loading: false,
          error: null,
          registrationState: 'unknown',
          connectionState: 'ready',
          connectionMessage: '',
        }));
      }
    });

    return () => unsubscribe();
  }, [fetchProfile, warmupBackend]);

  /**
   * Sign in with email/password
   * 
   * IMPORTANT: Returns { needsRegistration: true } if Firebase login succeeds
   * but user has no backend profile. This is NOT an error - user should be
   * redirected to complete registration.
   */
  const signIn = async (email: string, password: string): Promise<{ needsRegistration: boolean }> => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const result = await signInWithEmailAndPassword(auth, email, password);
      const profile = await fetchProfile(result.user);
      
      if (!profile) {
        // Firebase login succeeded but no backend profile
        // User needs to complete registration - NOT an error
        setState(prev => ({
          ...prev,
          user: result.user,
          profile: null,
          loading: false,
          error: null,
          registrationState: 'incomplete',
        }));
        return { needsRegistration: true };
      }
      
      // Check account status
      if (profile.accountStatus === 'SUSPENDED') {
        await firebaseSignOut(auth);
        const error = 'Your account has been suspended. Please contact support.';
        setState(prev => ({ ...prev, loading: false, error }));
        throw new Error(error);
      }
      
      setState(prev => ({
        ...prev,
        user: result.user,
        profile,
        loading: false,
        error: null,
        registrationState: 'complete',
      }));
      
      return { needsRegistration: false };
    } catch (error: unknown) {
      // Don't treat "profile not found" as error - already handled above
      if (state.registrationState === 'incomplete') {
        return { needsRegistration: true };
      }
      
      const message = getAuthErrorMessage(error);
      setState(prev => ({ ...prev, loading: false, error: message, registrationState: 'unknown' }));
      throw new Error(message);
    }
  };

  /**
   * Sign up with email/password and register in backend
   * Creates both Firebase account AND backend profile
   */
  const signUp = async (
    email: string, 
    password: string, 
    profileData: {
      businessName: string;
      phone: string;
      city: string;
      state: string;
      pincode: string;
    }
  ) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      // Create Firebase user
      const result = await createUserWithEmailAndPassword(auth, email, password);
      
      // Send verification email (don't block on this)
      sendEmailVerification(result.user).catch(() => {
        // Silently fail - user can request verification later
      });
      
      // Get token and register in backend
      const token = await result.user.getIdToken();
      
      try {
        await registerUser(token, {
          email,
          firebaseUid: result.user.uid,
          ...profileData,
        });
      } catch (regError) {
        // Handle specific registration errors
        if (regError instanceof ApiError) {
          if (regError.status === 409) {
            // User already exists in backend - try to fetch profile
            const existingProfile = await fetchProfile(result.user);
            if (existingProfile) {
              setState(prev => ({
                ...prev,
                user: result.user,
                profile: existingProfile,
                loading: false,
                error: null,
                registrationState: 'complete',
              }));
              return;
            }
          }
          throw new Error(regError.getUserMessage());
        }
        throw regError;
      }
      
      // Fetch the created profile
      const profile = await getUserProfile(token);
      
      setState(prev => ({
        ...prev,
        user: result.user,
        profile,
        loading: false,
        error: null,
        registrationState: 'complete',
      }));
    } catch (error: unknown) {
      const message = getAuthErrorMessage(error);
      setState(prev => ({ ...prev, loading: false, error: message }));
      throw new Error(message);
    }
  };

  /**
   * Complete registration for users who have Firebase account but no backend profile
   * Called when user logs in and needsRegistration is true
   */
  const completeRegistration = async (profileData: {
    businessName: string;
    phone: string;
    city: string;
    state: string;
    pincode: string;
  }) => {
    if (!state.user) {
      throw new Error('No user logged in');
    }
    
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const token = await state.user.getIdToken();
      
      await registerUser(token, {
        email: state.user.email || '',
        firebaseUid: state.user.uid,
        ...profileData,
      });
      
      // Fetch the created profile
      const profile = await getUserProfile(token);
      
      setState(prev => ({
        ...prev,
        user: state.user,
        profile,
        loading: false,
        error: null,
        registrationState: 'complete',
      }));
    } catch (error: unknown) {
      const message = getAuthErrorMessage(error);
      setState(prev => ({ ...prev, loading: false, error: message }));
      throw new Error(message);
    }
  };

  // Sign out
  const signOut = async () => {
    try {
      await firebaseSignOut(auth);
    } catch {
      // Silently handle sign out errors
    }
    setState(prev => ({
      ...prev,
      user: null,
      profile: null,
      loading: false,
      error: null,
      registrationState: 'unknown',
    }));
  };

  // Reset password
  const resetPassword = async (email: string) => {
    try {
      await sendPasswordResetEmail(auth, email);
    } catch (error: unknown) {
      const message = getAuthErrorMessage(error);
      throw new Error(message);
    }
  };

  // Get ID token - never logs it
  const getIdToken = async (): Promise<string | null> => {
    if (!state.user) return null;
    try {
      return await state.user.getIdToken();
    } catch {
      return null;
    }
  };

  // Refresh profile from backend
  const refreshProfile = async () => {
    if (!state.user) return;
    
    try {
      const profile = await fetchProfile(state.user);
      setState(prev => ({ 
        ...prev, 
        profile,
        registrationState: profile ? 'complete' : 'incomplete',
      }));
    } catch (error) {
      // Handle auth errors by signing out
      if (error instanceof ApiError && error.isAuthError()) {
        await signOut();
      }
    }
  };

  // Clear error
  const clearError = () => {
    setState(prev => ({ ...prev, error: null }));
  };

  // Computed properties
  const isAuthenticated = !!state.user && !!state.profile;
  // SSOT: Use camelCase field names to match database schema
  const isAdmin = state.profile?.isAdmin === true;
  const isSeller = state.profile?.isSeller === true;
  const needsRegistration = state.registrationState === 'incomplete';
  
  const role: UserRole = !state.user 
    ? 'guest' 
    : !state.profile
      ? 'guest'  // Not fully registered
      : isAdmin 
        ? 'admin' 
        : isSeller 
          ? 'seller' 
          : 'buyer';

  return (
    <AuthContext.Provider
      value={{
        ...state,
        isAuthenticated,
        isAdmin,
        isSeller,
        role,
        needsRegistration,
        signIn,
        signUp,
        completeRegistration,
        signOut,
        resetPassword,
        getIdToken,
        refreshProfile,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Helper to get user-friendly auth error messages
function getAuthErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.getUserMessage();
  }
  
  if (error instanceof Error) {
    // Firebase error codes
    const errorCode = (error as { code?: string }).code;
    switch (errorCode) {
      case 'auth/user-not-found':
      case 'auth/wrong-password':
      case 'auth/invalid-credential':
        return 'Invalid email or password';
      case 'auth/email-already-in-use':
        return 'This email is already registered';
      case 'auth/weak-password':
        return 'Password must be at least 6 characters';
      case 'auth/invalid-email':
        return 'Please enter a valid email address';
      case 'auth/too-many-requests':
        return 'Too many failed attempts. Please try again later';
      case 'auth/network-request-failed':
        return 'Network error. Please check your connection';
      default:
        return error.message || 'Authentication failed';
    }
  }
  
  return 'An unexpected error occurred';
}
