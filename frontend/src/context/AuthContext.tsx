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
  emailVerified: boolean;
}

interface AuthContextType extends AuthState {
  isAuthenticated: boolean;
  isAdmin: boolean;
  isSeller: boolean;
  isGstVerified: boolean;
  role: UserRole;
  needsRegistration: boolean;
  needsEmailVerification: boolean;
  
  signIn: (email: string, password: string) => Promise<{ needsRegistration: boolean; needsEmailVerification: boolean }>;
  signUp: (email: string, password: string) => Promise<{ needsEmailVerification: boolean }>;
  completeRegistration: (profileData: ProfileCompleteData) => Promise<void>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  resendVerificationEmail: () => Promise<void>;
  getIdToken: () => Promise<string | null>;
  refreshProfile: () => Promise<void>;
  checkEmailVerification: () => Promise<boolean>;
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
    emailVerified: false,
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

  const determineRegistrationState = useCallback((user: User, profile: UserProfile | null): RegistrationState => {
    // NEW ARCHITECTURE: Check profileComplete flag
    if (profile && profile.profileComplete) return 'complete';
    if (!user.emailVerified) return 'email_not_verified';
    // User exists but profile not completed
    if (profile && !profile.profileComplete) return 'incomplete';
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
            registrationState: regState, emailVerified: user.emailVerified,
            connectionState: 'ready', connectionMessage: 'Connected',
          }));
        } catch {
          setState(prev => ({
            ...prev, user, profile: null, loading: false,
            error: 'Failed to load profile.', registrationState: 'unknown',
            emailVerified: user.emailVerified, connectionState: 'error',
            connectionMessage: 'Connection error',
          }));
        }
      } else {
        setState(prev => ({
          ...prev, user: null, profile: null, loading: false,
          error: null, registrationState: 'unknown', emailVerified: false,
          connectionState: 'ready', connectionMessage: '',
        }));
      }
    });
    return () => unsubscribe();
  }, [fetchProfile, warmupBackend, determineRegistrationState]);

  const signIn = async (email: string, password: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const result = await signInWithEmailAndPassword(auth, email, password);
      
      // NEW ARCHITECTURE: Force token refresh to get latest email_verified status
      await result.user.reload();
      const freshToken = await result.user.getIdToken(true);
      
      if (!result.user.emailVerified) {
        setState(prev => ({
          ...prev, user: result.user, profile: null, loading: false,
          error: null, registrationState: 'email_not_verified', emailVerified: false,
        }));
        return { needsRegistration: false, needsEmailVerification: true };
      }
      
      // Fetch profile - this will auto-create user in MongoDB if needed
      const profile = await fetchProfile(result.user);
      
      // Check if profile is complete
      if (!profile || !profile.profileComplete) {
        setState(prev => ({
          ...prev, user: result.user, profile, loading: false,
          error: null, registrationState: 'incomplete', emailVerified: true,
        }));
        return { needsRegistration: true, needsEmailVerification: false };
      }
      
      setState(prev => ({
        ...prev, user: result.user, profile, loading: false,
        error: null, registrationState: 'complete', emailVerified: true,
      }));
      return { needsRegistration: false, needsEmailVerification: false };
    } catch (error: unknown) {
      const message = getAuthErrorMessage(error);
      setState(prev => ({ ...prev, loading: false, error: message }));
      throw new Error(message);
    }
  };

  const signUp = async (email: string, password: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const result = await createUserWithEmailAndPassword(auth, email, password);
      await sendEmailVerification(result.user);
      setState(prev => ({
        ...prev, user: result.user, profile: null, loading: false,
        error: null, registrationState: 'email_not_verified', emailVerified: false,
      }));
      return { needsEmailVerification: true };
    } catch (error: unknown) {
      const message = getAuthErrorMessage(error);
      setState(prev => ({ ...prev, loading: false, error: message }));
      throw new Error(message);
    }
  };

  const completeRegistrationHandler = async (profileData: ProfileCompleteData) => {
    if (!state.user) throw new Error('No user logged in');
    if (!state.user.emailVerified) throw new Error('Email verification required');
    
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const token = await state.user.getIdToken();
      const response = await completeProfile(token, profileData);
      setState(prev => ({
        ...prev, user: state.user, profile: response.user, loading: false,
        error: null, registrationState: 'complete', emailVerified: true,
      }));
    } catch (error: unknown) {
      const message = getAuthErrorMessage(error);
      setState(prev => ({ ...prev, loading: false, error: message }));
      throw new Error(message);
    }
  };

  const resendVerificationEmail = async () => {
    if (!state.user) throw new Error('No user logged in');
    await sendEmailVerification(state.user);
  };

  const checkEmailVerification = async (): Promise<boolean> => {
    if (!state.user) return false;
    try {
      await state.user.reload();
      const verified = state.user.emailVerified;
      if (verified && state.registrationState === 'email_not_verified') {
        setState(prev => ({ ...prev, registrationState: 'incomplete', emailVerified: true }));
      }
      return verified;
    } catch { return false; }
  };

  const signOut = async () => {
    try { await firebaseSignOut(auth); } catch {}
    setState(prev => ({
      ...prev, user: null, profile: null, loading: false,
      error: null, registrationState: 'unknown', emailVerified: false,
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
      setState(prev => ({ ...prev, profile, registrationState: profile ? 'complete' : 'incomplete' }));
    } catch {}
  };

  const clearError = () => setState(prev => ({ ...prev, error: null }));

  // ROLES-BASED COMPUTED PROPERTIES - derived from roles array
  const isAuthenticated = !!state.user && !!state.profile;
  const roles = state.profile?.roles ?? [];
  const isSeller = roles.includes('seller');
  const isAdmin = roles.includes('admin') || state.profile?.isAdmin === true;
  const isGstVerified = state.profile?.gstStatus === 'VERIFIED';
  const needsRegistration = state.registrationState === 'incomplete';
  const needsEmailVerification = state.registrationState === 'email_not_verified';
  
  const role: UserRole = !state.user ? 'guest' : !state.profile ? 'guest' : isAdmin ? 'admin' : isSeller ? 'seller' : 'buyer';

  return (
    <AuthContext.Provider value={{
      ...state, isAuthenticated, isAdmin, isSeller, isGstVerified, role,
      needsRegistration, needsEmailVerification, signIn, signUp,
      completeRegistration: completeRegistrationHandler, signOut, resetPassword,
      resendVerificationEmail, getIdToken, refreshProfile, checkEmailVerification, clearError,
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
