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
import { getUserProfile, registerUser, ApiError, warmBackend, checkRegistrationStatus, completeProfile, ProfileCompleteData } from '@/lib/api';
import type { UserProfile } from '@/types';

// User roles for role-based access control
export type UserRole = 'guest' | 'buyer' | 'seller' | 'admin';

// Registration state for users who have Firebase account but no backend profile
export type RegistrationState = 'complete' | 'incomplete' | 'email_not_verified' | 'unknown';

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
  emailVerified: boolean;
}

interface AuthContextType extends AuthState {
  // Computed properties
  isAuthenticated: boolean;
  isAdmin: boolean;
  isSeller: boolean;
  isGstVerified: boolean;
  role: UserRole;
  needsRegistration: boolean;
  needsEmailVerification: boolean;
  
  // Auth actions
  signIn: (email: string, password: string) => Promise<{ needsRegistration: boolean; needsEmailVerification: boolean }>;
  signUp: (email: string, password: string) => Promise<{ needsEmailVerification: boolean }>;
  completeRegistration: (profileData: ProfileCompleteData) => Promise<void>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  resendVerificationEmail: () => Promise<void>;
  
  // Token management
  getIdToken: () => Promise<string | null>;
  
  // Profile management
  refreshProfile: () => Promise<void>;
  checkEmailVerification: () => Promise<boolean>;
  
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
    emailVerified: false,
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

  // PHASE 1: Determine registration state based on email verification and profile
  const determineRegistrationState = useCallback((user: User, profile: UserProfile | null): RegistrationState => {
    if (profile) {
      return 'complete';
    }
    if (!user.emailVerified) {
      return 'email_not_verified';
    }
    return 'incomplete'; // Email verified but no profile
  }, []);

  // Initialize auth state listener
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        try {
          // Warm backend before fetching profile
          await warmupBackend();
          
          const profile = await fetchProfile(user);
          const regState = determineRegistrationState(user, profile);
          
          setState(prev => ({
            ...prev,
            user,
            profile,
            loading: false,
            error: null,
            registrationState: regState,
            emailVerified: user.emailVerified,
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
            emailVerified: user.emailVerified,
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
          emailVerified: false,
          connectionState: 'ready',
          connectionMessage: '',
        }));
      }
    });

    return () => unsubscribe();
  }, [fetchProfile, warmupBackend, determineRegistrationState]);

  /**
   * PHASE 1 - Sign in with email/password
   * 
   * Flow:
   * 1. Firebase login
   * 2. Check email_verified
   * 3. If not verified -> needsEmailVerification: true
   * 4. Check if MongoDB profile exists
   * 5. If no profile -> needsRegistration: true
   */
  const signIn = async (email: string, password: string): Promise<{ needsRegistration: boolean; needsEmailVerification: boolean }> => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const result = await signInWithEmailAndPassword(auth, email, password);
      
      // PHASE 1: Check email verification first
      if (!result.user.emailVerified) {
        setState(prev => ({
          ...prev,
          user: result.user,
          profile: null,
          loading: false,
          error: null,
          registrationState: 'email_not_verified',
          emailVerified: false,
        }));
        return { needsRegistration: false, needsEmailVerification: true };
      }
      
      const profile = await fetchProfile(result.user);
      
      if (!profile) {
        // Firebase login succeeded, email verified, but no backend profile
        // User needs to complete profile with role selection
        setState(prev => ({
          ...prev,
          user: result.user,
          profile: null,
          loading: false,
          error: null,
          registrationState: 'incomplete',
          emailVerified: true,
        }));
        return { needsRegistration: true, needsEmailVerification: false };
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
        emailVerified: true,
      }));
      
      return { needsRegistration: false, needsEmailVerification: false };
    } catch (error: unknown) {
      // Don't treat "profile not found" as error - already handled above
      if (state.registrationState === 'incomplete') {
        return { needsRegistration: true, needsEmailVerification: false };
      }
      if (state.registrationState === 'email_not_verified') {
        return { needsRegistration: false, needsEmailVerification: true };
      }
      
      const message = getAuthErrorMessage(error);
      setState(prev => ({ ...prev, loading: false, error: message, registrationState: 'unknown' }));
      throw new Error(message);
    }
  };

  /**
   * PHASE 1 - Sign up: Only create Firebase user, send verification email
   * DO NOT create MongoDB user yet - that happens after email verification
   */
  const signUp = async (email: string, password: string): Promise<{ needsEmailVerification: boolean }> => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      // Create Firebase user only
      const result = await createUserWithEmailAndPassword(auth, email, password);
      
      // Send verification email
      await sendEmailVerification(result.user);
      
      setState(prev => ({
        ...prev,
        user: result.user,
        profile: null,
        loading: false,
        error: null,
        registrationState: 'email_not_verified',
        emailVerified: false,
      }));
      
      return { needsEmailVerification: true };
    } catch (error: unknown) {
      const message = getAuthErrorMessage(error);
      setState(prev => ({ ...prev, loading: false, error: message }));
      throw new Error(message);
    }
  };

  /**
   * PHASE 2 - Complete registration with role selection
   * Called after email verification
   */
  const completeRegistrationHandler = async (profileData: ProfileCompleteData) => {
    if (!state.user) {
      throw new Error('No user logged in');
    }
    
    // PHASE 1: Require email verification
    if (!state.user.emailVerified) {
      throw new Error('Email verification required before completing registration');
    }
    
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const token = await state.user.getIdToken();
      
      const response = await completeProfile(token, profileData);
      
      setState(prev => ({
        ...prev,
        user: state.user,
        profile: response.user,
        loading: false,
        error: null,
        registrationState: 'complete',
        emailVerified: true,
      }));
    } catch (error: unknown) {
      const message = getAuthErrorMessage(error);
      setState(prev => ({ ...prev, loading: false, error: message }));
      throw new Error(message);
    }
  };

  // Resend verification email
  const resendVerificationEmail = async () => {
    if (!state.user) {
      throw new Error('No user logged in');
    }
    
    try {
      await sendEmailVerification(state.user);
    } catch (error: unknown) {
      const message = getAuthErrorMessage(error);
      throw new Error(message);
    }
  };

  // Check if email has been verified (reload user)
  const checkEmailVerification = async (): Promise<boolean> => {
    if (!state.user) {
      return false;
    }
    
    try {
      await state.user.reload();
      const verified = state.user.emailVerified;
      
      if (verified && state.registrationState === 'email_not_verified') {
        setState(prev => ({
          ...prev,
          registrationState: 'incomplete',
          emailVerified: true,
        }));
      }
      
      return verified;
    } catch {
      return false;
    }
  };

  // LEGACY signUp with profile data (for backwards compatibility)
  const legacySignUp = async (
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
