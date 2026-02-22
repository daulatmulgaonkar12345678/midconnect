import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy - MidConnect',
  description: 'Learn how MidConnect collects, uses, and protects your personal and business information.',
};

export default function PrivacyPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-4xl font-bold text-gray-900 mb-8">Privacy Policy</h1>
      
      <div className="prose prose-lg max-w-none text-gray-600">
        <p className="text-sm text-gray-500 mb-8">Last updated: February 2026</p>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">1. Information We Collect</h2>
          <p>We collect the following types of information:</p>
          <ul className="list-disc pl-6 mt-2 space-y-2">
            <li><strong>Account Information:</strong> Email, password, business name, phone number, address</li>
            <li><strong>Business Information:</strong> GST number, GST certificate, business documents</li>
            <li><strong>Usage Data:</strong> How you interact with our platform, search queries, browsing history</li>
            <li><strong>Device Information:</strong> IP address, browser type, device type</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">2. How We Use Your Information</h2>
          <p>Your information is used to:</p>
          <ul className="list-disc pl-6 mt-2 space-y-2">
            <li>Create and manage your account</li>
            <li>Verify your business credentials</li>
            <li>Connect you with buyers or sellers</li>
            <li>Process transactions and enquiries</li>
            <li>Send important notifications and updates</li>
            <li>Improve our platform and services</li>
            <li>Prevent fraud and ensure security</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">3. Information Sharing</h2>
          <p>We may share your information with:</p>
          <ul className="list-disc pl-6 mt-2 space-y-2">
            <li><strong>Other Users:</strong> Business information shared with potential buyers/sellers</li>
            <li><strong>Service Providers:</strong> Third parties helping us operate the platform</li>
            <li><strong>Legal Requirements:</strong> When required by law or legal process</li>
          </ul>
          <p className="mt-4">
            We do not sell your personal information to third parties for marketing purposes.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">4. Data Security</h2>
          <p>
            We implement industry-standard security measures to protect your data, including:
          </p>
          <ul className="list-disc pl-6 mt-2 space-y-2">
            <li>Encryption of data in transit and at rest</li>
            <li>Secure authentication using Firebase</li>
            <li>Regular security audits and monitoring</li>
            <li>Access controls and employee training</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">5. Data Retention</h2>
          <p>
            We retain your data for as long as your account is active or as needed to provide 
            services. After account deletion, we may retain certain data for legal compliance 
            or legitimate business purposes for up to 7 years.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">6. Your Rights</h2>
          <p>You have the right to:</p>
          <ul className="list-disc pl-6 mt-2 space-y-2">
            <li>Access your personal data</li>
            <li>Correct inaccurate data</li>
            <li>Request deletion of your data</li>
            <li>Export your data</li>
            <li>Opt out of marketing communications</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">7. Cookies</h2>
          <p>
            We use cookies and similar technologies to improve user experience, analyze usage, 
            and provide personalized content. You can control cookie preferences through your 
            browser settings.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">8. Changes to Privacy Policy</h2>
          <p>
            We may update this policy from time to time. We will notify you of significant 
            changes via email or platform notification.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">9. Contact Us</h2>
          <p>
            For privacy-related questions or to exercise your rights, contact us at:
            <br />
            Email: privacy@b2bmarket.in
          </p>
        </section>
      </div>
    </div>
  );
}
