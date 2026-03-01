'use client';

import { useState } from 'react';
import { Mail, Phone, MapPin, Clock, MessageCircle, Loader2, CheckCircle, AlertCircle } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';

export default function ContactPage() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [statusMessage, setStatusMessage] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    if (!formData.name || !formData.email || !formData.subject || !formData.message) {
      setSubmitStatus('error');
      setStatusMessage('Please fill in all fields');
      return;
    }

    if (formData.message.length < 10) {
      setSubmitStatus('error');
      setStatusMessage('Message must be at least 10 characters');
      return;
    }

    setIsSubmitting(true);
    setSubmitStatus('idle');

    try {
      const response = await fetch(`${API_URL}/api/contact`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setSubmitStatus('success');
        setStatusMessage(data.message || 'Message sent successfully!');
        // Reset form
        setFormData({ name: '', email: '', subject: '', message: '' });
      } else {
        setSubmitStatus('error');
        setStatusMessage(data.detail || data.message || 'Failed to send message. Please try again.');
      }
    } catch (error) {
      console.error('Contact form error:', error);
      setSubmitStatus('error');
      setStatusMessage('Network error. Please check your connection and try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Contact Us</h1>
        <p className="text-xl text-gray-600">
          We&apos;re here to help. Reach out to us with any questions or concerns.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Contact Information */}
        <div className="space-y-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Get In Touch</h2>
          
          <div className="flex items-start gap-4">
            <div className="bg-blue-100 p-3 rounded-lg">
              <Mail className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Email Support</h3>
              <p className="text-gray-600">support@udyogconnect.in</p>
              <p className="text-sm text-gray-500">We respond within 24 hours</p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="bg-green-100 p-3 rounded-lg">
              <Phone className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Phone Support</h3>
              <a href="tel:+917387821042" className="text-gray-600 hover:text-green-600">
                +91 73878 21042
              </a>
              <p className="text-sm text-gray-500">Mon-Sat, 9 AM - 6 PM IST</p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="bg-purple-100 p-3 rounded-lg">
              <MessageCircle className="h-6 w-6 text-purple-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">WhatsApp</h3>
              <a
                href="https://wa.me/917387821042"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-600 hover:text-green-600"
              >
                +91 73878 21042
              </a>
              <p className="text-sm text-gray-500">Quick responses for urgent queries</p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="bg-orange-100 p-3 rounded-lg">
              <Clock className="h-6 w-6 text-orange-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Business Hours</h3>
              <p className="text-gray-600">Monday - Saturday</p>
              <p className="text-sm text-gray-500">9:00 AM - 6:00 PM IST</p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="bg-red-100 p-3 rounded-lg">
              <MapPin className="h-6 w-6 text-red-600" />
            </div>
            <div className="space-y-5">
              <div>
                <h3 className="font-semibold text-gray-900">Head Office – Pune</h3>
                <p className="text-gray-600">
                  D2, Kedareshwar Park, Gujarwadi, Katraj, Pune – 411046
                </p>
                <p className="text-sm text-gray-500">Maharashtra, India</p>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Branch Office – Kolhapur</h3>
                <p className="text-gray-600">
                  Plot No. 12, Near Tulips Residency,<br />
                  Behind Circuit House, Kolhapur – 416003
                </p>
                <p className="text-sm text-gray-500">Maharashtra, India</p>
              </div>
            </div>
          </div>
        </div>

        {/* Contact Form */}
        <div className="bg-white rounded-xl shadow-lg p-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Send us a Message</h2>
          
          {/* Status Messages */}
          {submitStatus === 'success' && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3">
              <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
              <p className="text-green-700">{statusMessage}</p>
            </div>
          )}
          
          {submitStatus === 'error' && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
              <p className="text-red-700">{statusMessage}</p>
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                Your Name
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your name"
                disabled={isSubmitting}
                required
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email Address
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="you@example.com"
                disabled={isSubmitting}
                required
              />
            </div>

            <div>
              <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-1">
                Subject
              </label>
              <select
                id="subject"
                name="subject"
                value={formData.subject}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isSubmitting}
                required
              >
                <option value="">Select a topic</option>
                <option value="general">General Inquiry</option>
                <option value="support">Technical Support</option>
                <option value="seller">Seller Support</option>
                <option value="buyer">Buyer Support</option>
                <option value="feedback">Feedback</option>
              </select>
            </div>

            <div>
              <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-1">
                Message
              </label>
              <textarea
                id="message"
                name="message"
                rows={4}
                value={formData.message}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="How can we help you?"
                disabled={isSubmitting}
                required
                minLength={10}
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Sending...
                </>
              ) : (
                'Send Message'
              )}
            </button>
          </form>

          <p className="text-xs text-gray-500 mt-4 text-center">
            By submitting, you agree to our Privacy Policy
          </p>
        </div>
      </div>
    </div>
  );
}
