'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
  getWhatsAppContacts,
  addWhatsAppContact,
  updateWhatsAppContact,
  deleteWhatsAppContact,
  setWhatsAppPrimaryContact,
  getWhatsAppSettings,
  updateWhatsAppSettings,
  WhatsAppContact
} from '@/lib/api';
import {
  Loader2,
  ArrowLeft,
  Phone,
  Plus,
  Trash2,
  Edit2,
  Star,
  Check,
  X,
  MessageCircle,
  Settings,
  AlertCircle,
  Info
} from 'lucide-react';
import Link from 'next/link';

export default function SellerWhatsAppPage() {
  const router = useRouter();
  const { user, getIdToken, loading: authLoading } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Data state
  const [contacts, setContacts] = useState<WhatsAppContact[]>([]);
  const [autoConnect, setAutoConnect] = useState(true);
  
  // Form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingContact, setEditingContact] = useState<string | null>(null);
  const [formPhone, setFormPhone] = useState('');
  const [formLabel, setFormLabel] = useState('');
  const [formIsPrimary, setFormIsPrimary] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  // Delete confirmation
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const token = await getIdToken();
      if (!token) {
        router.push('/login');
        return;
      }

      const [contactsRes, settingsRes] = await Promise.all([
        getWhatsAppContacts(token),
        getWhatsAppSettings(token)
      ]);

      setContacts(contactsRes.contacts);
      setAutoConnect(settingsRes.autoWhatsappConnect);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load data';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [getIdToken, router]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    } else if (!authLoading && user) {
      loadData();
    }
  }, [user, authLoading, router, loadData]);

  const resetForm = () => {
    setFormPhone('');
    setFormLabel('');
    setFormIsPrimary(false);
    setShowAddForm(false);
    setEditingContact(null);
  };

  const handleAddContact = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) return;

      // Clean phone number
      let cleanPhone = formPhone.replace(/[\s\-\(\)]/g, '');
      if (!cleanPhone.startsWith('+')) {
        cleanPhone = '+91' + cleanPhone; // Default to India
      }

      await addWhatsAppContact(token, {
        phoneNumber: cleanPhone,
        label: formLabel || undefined,
        isPrimary: formIsPrimary
      });

      setSuccess('WhatsApp contact added successfully');
      resetForm();
      loadData();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to add contact';
      setError(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateContact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingContact) return;
    
    setSubmitting(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) return;

      // Clean phone number
      let cleanPhone = formPhone.replace(/[\s\-\(\)]/g, '');
      if (!cleanPhone.startsWith('+')) {
        cleanPhone = '+91' + cleanPhone;
      }

      await updateWhatsAppContact(token, editingContact, {
        phoneNumber: cleanPhone,
        label: formLabel || undefined,
        isPrimary: formIsPrimary
      });

      setSuccess('Contact updated successfully');
      resetForm();
      loadData();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update contact';
      setError(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (contactId: string) => {
    try {
      const token = await getIdToken();
      if (!token) return;

      await deleteWhatsAppContact(token, contactId);
      setSuccess('Contact deleted');
      setDeletingId(null);
      loadData();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete contact';
      setError(errorMessage);
    }
  };

  const handleSetPrimary = async (contactId: string) => {
    try {
      const token = await getIdToken();
      if (!token) return;

      await setWhatsAppPrimaryContact(token, contactId);
      setSuccess('Primary contact updated');
      loadData();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to set primary';
      setError(errorMessage);
    }
  };

  const handleToggleAutoConnect = async () => {
    try {
      const token = await getIdToken();
      if (!token) return;

      const newValue = !autoConnect;
      await updateWhatsAppSettings(token, { autoWhatsappConnect: newValue });
      setAutoConnect(newValue);
      setSuccess(newValue ? 'Auto connect enabled' : 'Auto connect disabled');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update settings';
      setError(errorMessage);
    }
  };

  const startEditing = (contact: WhatsAppContact) => {
    setEditingContact(contact.id);
    setFormPhone(contact.phoneNumber);
    setFormLabel(contact.label || '');
    setFormIsPrimary(contact.isPrimary);
    setShowAddForm(false);
  };

  // Auto-clear messages
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50" data-testid="whatsapp-settings-page">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link href="/seller" className="p-2 hover:bg-gray-100 rounded-lg" data-testid="back-btn">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <MessageCircle className="h-5 w-5 text-green-600" />
                WhatsApp Inquiry Contacts
              </h1>
              <p className="text-sm text-gray-500">Manage your WhatsApp numbers for buyer inquiries</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Error/Success Messages */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3" data-testid="error-message">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
            <p className="text-red-700">{error}</p>
            <button onClick={() => setError(null)} className="ml-auto">
              <X className="h-4 w-4 text-red-500" />
            </button>
          </div>
        )}
        
        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3" data-testid="success-message">
            <Check className="h-5 w-5 text-green-500 flex-shrink-0" />
            <p className="text-green-700">{success}</p>
          </div>
        )}

        {/* Auto Connect Toggle */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Settings className="h-5 w-5 text-gray-500" />
              <div>
                <h3 className="font-medium text-gray-900">Auto Connect via WhatsApp</h3>
                <p className="text-sm text-gray-500">
                  When enabled, buyers can connect with you on WhatsApp after sending an inquiry
                </p>
              </div>
            </div>
            <button
              onClick={handleToggleAutoConnect}
              className={`relative w-14 h-7 rounded-full transition-colors ${
                autoConnect ? 'bg-green-500' : 'bg-gray-300'
              }`}
              data-testid="auto-connect-toggle"
            >
              <span
                className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                  autoConnect ? 'left-8' : 'left-1'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex gap-3">
            <Info className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-700">
              <p className="font-medium mb-1">How it works:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Add your WhatsApp numbers below</li>
                <li>Set one number as <strong>Primary</strong> - this will be used for buyer connections</li>
                <li>In your inquiry dashboard, you can choose different numbers to contact buyers</li>
                <li>We recommend keeping 3-5 numbers for easy management</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Contacts Table */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="p-4 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <Phone className="h-5 w-5 text-gray-500" />
              WhatsApp Numbers ({contacts.length})
            </h2>
            <button
              onClick={() => { resetForm(); setShowAddForm(true); }}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              data-testid="add-contact-btn"
            >
              <Plus className="h-4 w-4" />
              Add Contact
            </button>
          </div>

          {/* Add Form */}
          {showAddForm && (
            <div className="p-4 border-b bg-gray-50">
              <form onSubmit={handleAddContact} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Phone Number *
                    </label>
                    <input
                      type="tel"
                      value={formPhone}
                      onChange={(e) => setFormPhone(e.target.value)}
                      placeholder="+91 98765 43210"
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                      required
                      data-testid="phone-input"
                    />
                    <p className="text-xs text-gray-500 mt-1">Include country code (e.g., +91)</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Label (Optional)
                    </label>
                    <input
                      type="text"
                      value={formLabel}
                      onChange={(e) => setFormLabel(e.target.value)}
                      placeholder="Sales / Support / Manager"
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                      data-testid="label-input"
                    />
                  </div>
                  <div className="flex items-end">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formIsPrimary}
                        onChange={(e) => setFormIsPrimary(e.target.checked)}
                        className="w-4 h-4 text-green-600 rounded"
                        data-testid="primary-checkbox"
                      />
                      <span className="text-sm text-gray-700">Set as Primary</span>
                    </label>
                  </div>
                </div>
                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                    data-testid="save-contact-btn"
                  >
                    {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                    Save Contact
                  </button>
                  <button
                    type="button"
                    onClick={resetForm}
                    className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Contacts List */}
          {contacts.length === 0 ? (
            <div className="p-8 text-center">
              <MessageCircle className="h-12 w-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No WhatsApp contacts added yet</p>
              <p className="text-sm text-gray-400 mt-1">
                Add your first contact to enable WhatsApp inquiry connections
              </p>
            </div>
          ) : (
            <div className="divide-y">
              {contacts.map((contact) => (
                <div key={contact.id} className="p-4 hover:bg-gray-50">
                  {editingContact === contact.id ? (
                    // Edit Form
                    <form onSubmit={handleUpdateContact} className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                          <input
                            type="tel"
                            value={formPhone}
                            onChange={(e) => setFormPhone(e.target.value)}
                            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
                            required
                          />
                        </div>
                        <div>
                          <input
                            type="text"
                            value={formLabel}
                            onChange={(e) => setFormLabel(e.target.value)}
                            placeholder="Label"
                            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500"
                          />
                        </div>
                        <div className="flex items-center gap-4">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={formIsPrimary}
                              onChange={(e) => setFormIsPrimary(e.target.checked)}
                              className="w-4 h-4 text-green-600 rounded"
                            />
                            <span className="text-sm">Primary</span>
                          </label>
                          <div className="flex gap-2 ml-auto">
                            <button
                              type="submit"
                              disabled={submitting}
                              className="p-2 bg-green-100 text-green-600 rounded-lg hover:bg-green-200"
                            >
                              <Check className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              onClick={resetForm}
                              className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    </form>
                  ) : (
                    // Display Row
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                          <Phone className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900" data-testid={`contact-phone-${contact.id}`}>
                              {contact.phoneNumber}
                            </span>
                            {contact.isPrimary && (
                              <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 text-xs font-medium rounded-full flex items-center gap-1">
                                <Star className="h-3 w-3" />
                                Primary
                              </span>
                            )}
                          </div>
                          {contact.label && (
                            <span className="text-sm text-gray-500">{contact.label}</span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {!contact.isPrimary && (
                          <button
                            onClick={() => handleSetPrimary(contact.id)}
                            className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg"
                            title="Set as Primary"
                            data-testid={`set-primary-${contact.id}`}
                          >
                            <Star className="h-4 w-4" />
                          </button>
                        )}
                        <button
                          onClick={() => startEditing(contact)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                          title="Edit"
                          data-testid={`edit-contact-${contact.id}`}
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>
                        {deletingId === contact.id ? (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleDelete(contact.id)}
                              className="p-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200"
                              title="Confirm Delete"
                            >
                              <Check className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => setDeletingId(null)}
                              className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
                              title="Cancel"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setDeletingId(contact.id)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                            title="Delete"
                            data-testid={`delete-contact-${contact.id}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
