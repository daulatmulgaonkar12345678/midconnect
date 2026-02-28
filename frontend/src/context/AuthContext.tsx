'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { 
  User,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  sendPasswordResetEmail
} from 'firebase/auth';
import { auth } from '@/lib/firebase';
import { getUserProfile, ApiError, warmBackend, completeProfile, ProfileCompleteData } from '@/lib/api';
import type { UserProfile } from '@/types';

export type UserRole = 'guest' | 'buyer' | 'seller' | 'admin';
export type RegistrationState = 'complete' | 'incomplete' | 'email_not_verified' | 'unknown';
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
  isAuthenticated: boolean;
  isAdmin: boolean;
  isSeller: boolean;
  isGstVerified: boolean;
  gstStatus: 'none' | 'pending' | 'verified' | 'rejected';
  sellerStatus: 'active' | 'suspended' | 'banned';
  role: UserRole;
  needsRegistration: boolean;
  needsEmailVerification: boolean;
  
  signIn: (email: string, password: string) => Promise<{ needsRegistration: boolean; needsEmailVerification: boolean }>;
  signUp: (email: string, password: string) => Promise<{ needsEmailVerification: boolean }>;
  completeRegistration: (profileData: ProfileCompleteData) => Promise<void>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  resendVerificationEmail: () => Promise<void>;  // ENTERPRISE FIX: No email param needed
  getIdToken: () => Promise<string | null>;
  refreshProfile: () => Promise<void>;
  clearError: () => void;
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

  const warmupBackend = useCallback(async () => {
    setState(prev => ({ ...prev, connectionState: 'connecting', connectionMessage: 'Connecting to server...' }));
    const result = await warmBackend();
    setState(prev => ({ ...prev, connectionState: result.ready ? 'ready' : 'connecting', connectionMessage: result.message }));
    return result.ready;
  }, []);

  const fetchProfile = useCallback(async (user: User): Promise<UserProfile | null> => {
    try {
      const token = await user.getIdToken();
      return await getUserProfile(token);
    } catch (error) {
      if (error instanceof ApiError && (error.status === 404 || error.status === 401)) {
        return null;
      }
      throw error;
    }
  }, []);

  /**
   * NEW ARCHITECTURE: Determine registration state based on backend profile
   * 
   * Uses profile.isEmailVerified from backend (NOT Firebase's emailVerified)
   * This gives us full control over email verification via Zoho SMTP
   */
  const determineRegistrationState = useCallback((user: User, profile: UserProfile | null): RegistrationState => {
    // Check backend's email verification status (not Firebase's)
    if (!profile?.isEmailVerified) return 'email_not_verified';
    if (profile?.profileComplete) return 'complete';
    return 'incomplete';
  }, []);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        try {
          await warmupBackend();
          const profile = await fetchProfile(user);
          const regState = determineRegistrationState(user, profile);
          
          setState(prev => ({
            ...prev, user, profile, loading: false, error: null,
            registrationState: regState,
            connectionState: 'ready', connectionMessage: 'Connected',
          }));
        } catch {
          setState(prev => ({
            ...prev, user, profile: null, loading: false,
            error: 'Failed to load profile.', registrationState: 'unknown',
            connectionState: 'error',
            connectionMessage: 'Connection error',
          }));
        }
      } else {
        setState(prev => ({
          ...prev, user: null, profile: null, loading: false,
          error: null, registrationState: 'unknown',
          connectionState: 'ready', connectionMessage: '',
        }));
      }
    });
    return () => unsubscribe();
  }, [fetchProfile, warmupBackend, determineRegistrationState]);

  /**
   * Sign in with email/password
   * 
   * NEW ARCHITECTURE: Check backend's isEmailVerified (not Firebase's emailVerified)
   */
  const signIn = async (email: string, password: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const result = await signInWithEmailAndPassword(auth, email, password);
      
      // Fetch profile from backend - this is the source of truth for verification status
      const profile = await fetchProfile(result.user);
      
      // NEW: Check backend's isEmailVerified status
      if (!profile?.isEmailVerified) {
        setState(prev => ({
          ...prev, user: result.user, profile, loading: false,
          error: null, registrationState: 'email_not_verified',
        }));
        return { needsRegistration: false, needsEmailVerification: true };
      }
      
      // Check if profile is complete
      if (!profile?.profileComplete) {
        setState(prev => ({
          ...prev, user: result.user, profile, loading: false,
          error: null, registrationState: 'incomplete',
        }));
        return { needsRegistration: true, needsEmailVerification: false };
      }
      
      setState(prev => ({
        ...prev, user: result.user, profile, loading: false,
        error: null, registrationState: 'complete',
      }));
      return { needsRegistration: false, needsEmailVerification: false };
      
    } catch (error: unknown) {
      const message = getAuthErrorMessage(error);
      setState(prev => ({ ...prev, loading: false, error: message }));
      throw new Error(message);
    }
  };

  /**
   * Sign up with email/password
   * 
   * ENTERPRISE FIX: 
   * 1. Firebase creates auth user
   * 2. Get token from Firebase
   * 3. Backend sends verification email via Zoho SMTP using token
   * 
   * IMPORTANT: We must get the token IMMEDIATELY after signup and call
   * the verification endpoint before onAuthStateChanged causes re-renders.
   */
  const signUp = async (email: string, password: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      // Step 1: Create Firebase auth user
      const result = await createUserWithEmailAndPassword(auth, email, password);
      
      // Step 2: Get token IMMEDIATELY (before onAuthStateChanged triggers)
      const token = await result.user.getIdToken();
      
      // Step 3: Call backend to send verification email using TOKEN (not email)
      // This is the ENTERPRISE FIX - backend gets email from token
      try {
        const { sendVerificationEmail } = await import('@/lib/api');
        await sendVerificationEmail(token);
        console.log('[Auth] Verification email sent successfully');
      } catch (emailError) {
        // Log but don't fail signup if email sending fails
        console.error('[Auth] Error sending verification email:', emailError);
      }
      
      setState(prev => ({
        ...prev, user: result.user, profile: null, loading: false,
        error: null, registrationState: 'email_not_verified',
      }));
      
      return { needsEmailVerification: true };
      
    } catch (error: unknown) {
      const message = getAuthErrorMessage(error);
      setState(prev => ({ ...prev, loading: false, error: message }));
      throw new Error(message);
    }
  };

  /**
   * Complete user registration/profile
   * 
   * NEW ARCHITECTURE: Check backend's isEmailVerified instead of Firebase
   */
  const completeRegistrationHandler = async (profileData: ProfileCompleteData) => {
    if (!state.user) throw new Error('No user logged in');
    
    // Check backend verification status via profile
    if (!state.profile?.isEmailVerified) {
      throw new Error('Email verification required. Please check your inbox.');
    }
    
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const token = await state.user.getIdToken();
      const response = await completeProfile(token, profileData);
      setState(prev => ({
        ...prev, user: state.user, profile: response.user, loading: false,
        error: null, registrationState: 'complete',
      }));
    } catch (error: unknown) {
      const message = getAuthErrorMessage(error);
      setState(prev => ({ ...prev, loading: false, error: message }));
      throw new Error(message);
    }
  };

  /**
   * Resend verification email via backend (Zoho SMTP)
   * 
   * ENTERPRISE FIX: Uses auth token, no email in body.
   * Backend gets user email from the Firebase auth token.
   */
  const resendVerificationEmail = async () => {
    if (!state.user) throw new Error('No user logged in');
    
    const token = await state.user.getIdToken();
    const { resendVerificationEmail: resendApi } = await import('@/lib/api');
    await resendApi(token);
  };

  const signOut = async () => {
    try { await firebaseSignOut(auth); } catch {}
    setState(prev => ({
      ...prev, user: null, profile: null, loading: false,
      error: null, registrationState: 'unknown',
    }));
  };

  const resetPassword = async (email: string) => {
    await sendPasswordResetEmail(auth, email);
  };

  const getIdToken = async () => {
    if (!state.user) return null;
    try { return await state.user.getIdToken(); } catch { return null; }
  };

  const refreshProfile = async () => {
    if (!state.user) return;
    try {
      const profile = await fetchProfile(state.user);
      const regState = determineRegistrationState(state.user, profile);
      setState(prev => ({ ...prev, profile, registrationState: regState }));
    } catch {}
  };

  const clearError = () => setState(prev => ({ ...prev, error: null }));

  // ROLES-BASED COMPUTED PROPERTIES - derived from roles array
  const isAuthenticated = !!state.user && !!state.profile && state.profile.profileComplete === true;
  const roles: string[] = state.profile?.roles ?? [];
  const isSeller = roles.includes('seller');
  const isAdmin = roles.includes('admin') || state.profile?.isAdmin === true;
  
  // UNIFIED GST SCHEMA - SINGLE SOURCE OF TRUTH
  const isGstVerified = state.profile?.gst?.verified === true;
  const gstStatus = (state.profile?.gst?.status || 'none') as 'none' | 'pending' | 'verified' | 'rejected';
  
  // Seller account status
  const sellerStatus = (state.profile?.sellerStatus || 'active') as 'active' | 'suspended' | 'banned';
  
  const needsRegistration = state.registrationState === 'incomplete';
  const needsEmailVerification = state.registrationState === 'email_not_verified';
  
  const role: UserRole = !state.user ? 'guest' : !state.profile?.profileComplete ? 'guest' : isAdmin ? 'admin' : isSeller ? 'seller' : 'buyer';

  return (
    <AuthContext.Provider value={{
      ...state, isAuthenticated, isAdmin, isSeller, isGstVerified, gstStatus, sellerStatus, role,
      needsRegistration, needsEmailVerification, signIn, signUp,
      completeRegistration: completeRegistrationHandler, signOut, resetPassword,
      resendVerificationEmail, getIdToken, refreshProfile, clearError,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}

function getAuthErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.getUserMessage();
  if (error instanceof Error) {
    const errorCode = (error as { code?: string }).code;
    switch (errorCode) {
      case 'auth/user-not-found':
      case 'auth/wrong-password':
      case 'auth/invalid-credential': return 'Invalid email or password';
      case 'auth/email-already-in-use': return 'This email is already registered';
      case 'auth/weak-password': return 'Password must be at least 6 characters';
      case 'auth/invalid-email': return 'Please enter a valid email address';
      case 'auth/too-many-requests': return 'Too many failed attempts. Please try again later';
      case 'auth/network-request-failed': return 'Network error. Please check your connection';
      default: return error.message || 'Authentication failed';
    }
  }
  return 'An unexpected error occurred';
}
