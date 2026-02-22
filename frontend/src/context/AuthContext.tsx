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
  const fetchProfile = useCallback(async (user: User): Promise<UserProfile | null> => {
    try {
      const token = await user.getIdToken();
      return await getUserProfile(token);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return null;
      }
      if (error instanceof ApiError && error.status === 401) {
        return null;
      }
      throw error;
    }
  }, []);

  // Determine registration state
  const determineRegistrationState = useCallback((user: User, profile: UserProfile | null): RegistrationState => {
    if (profile) {
      return 'complete';
    }
    if (!user.emailVerified) {
      return 'email_not_verified';
    }
    return 'incomplete';
  }, []);

  // Initialize auth state listener
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        try {
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

  // Sign in with email/password
  const signIn = async (email: string, password: string): Promise<{ needsRegistration: boolean; needsEmailVerification: boolean }> => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const result = await signInWithEmailAndPassword(auth, email, password);
      
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

  // Sign up - Only create Firebase user, send verification email
  const signUp = async (email: string, password: string): Promise<{ needsEmailVerification: boolean }> => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const result = await createUserWithEmailAndPassword(auth, email, password);
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

  // Complete registration with role selection
  const completeRegistrationHandler = async (profileData: ProfileCompleteData) => {
    if (!state.user) {
      throw new Error('No user logged in');
    }
    
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

  // Check if email has been verified
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
      emailVerified: false,
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

  // Get ID token
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
        registrationState: profile ? 'complete' : (state.user?.emailVerified ? 'incomplete' : 'email_not_verified'),
      }));
    } catch (error) {
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
  const isAdmin = state.profile?.isAdmin === true;
  const roles = state.profile?.roles || [];
  const isSeller = roles.includes('seller');
  const isGstVerified = state.profile?.gst?.verified === true;
  const needsRegistration = state.registrationState === 'incomplete';
  const needsEmailVerification = state.registrationState === 'email_not_verified';
  
  const role: UserRole = !state.user 
    ? 'guest' 
    : !state.profile
      ? 'guest'
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
        isGstVerified,
        role,
        needsRegistration,
        needsEmailVerification,
        signIn,
        signUp,
        completeRegistration: completeRegistrationHandler,
        signOut,
        resetPassword,
        resendVerificationEmail,
        getIdToken,
        refreshProfile,
        checkEmailVerification,
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
