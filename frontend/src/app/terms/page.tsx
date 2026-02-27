import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Terms of Service - UdyogConnect',
  description: 'Terms and conditions for using UdyogConnect platform. Read our terms of service before using our marketplace.',
};

export default function TermsPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-4xl font-bold text-gray-900 mb-8">Terms of Service</h1>
      
      <div className="prose prose-lg max-w-none text-gray-600">
        <p className="text-sm text-gray-500 mb-8">Last updated: February 2026</p>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">1. Acceptance of Terms</h2>
          <p>
            By accessing and using UdyogConnect ("the Platform"), you agree to be bound by these 
            Terms of Service. If you do not agree to these terms, please do not use our services.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">2. Eligibility</h2>
          <p>To use our Platform, you must:</p>
          <ul className="list-disc pl-6 mt-2 space-y-2">
            <li>Be at least 18 years of age</li>
            <li>Be a registered business entity in India</li>
            <li>Have a valid GST registration (for sellers)</li>
            <li>Provide accurate and complete registration information</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">3. User Accounts</h2>
          <p>
            You are responsible for maintaining the confidentiality of your account credentials 
            and for all activities that occur under your account. You must notify us immediately 
            of any unauthorized use of your account.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">4. Seller Obligations</h2>
          <p>Sellers on our platform agree to:</p>
          <ul className="list-disc pl-6 mt-2 space-y-2">
            <li>Provide accurate product descriptions and pricing</li>
            <li>Maintain valid GST registration</li>
            <li>Fulfill orders within stated lead times</li>
            <li>Respond to buyer enquiries promptly</li>
            <li>Comply with all applicable laws and regulations</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">5. Buyer Obligations</h2>
          <p>Buyers on our platform agree to:</p>
          <ul className="list-disc pl-6 mt-2 space-y-2">
            <li>Provide accurate business and contact information</li>
            <li>Make payments as per agreed terms</li>
            <li>Use the platform for legitimate business purposes only</li>
            <li>Not engage in fraudulent activities</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">6. Prohibited Activities</h2>
          <p>Users must not:</p>
          <ul className="list-disc pl-6 mt-2 space-y-2">
            <li>Post false, misleading, or fraudulent content</li>
            <li>Violate any intellectual property rights</li>
            <li>Attempt to gain unauthorized access to other accounts</li>
            <li>Use the platform for illegal purposes</li>
            <li>Spam or harass other users</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">7. Limitation of Liability</h2>
          <p>
            UdyogConnect acts as an intermediary platform connecting buyers and sellers. We are not 
            responsible for the quality, safety, or legality of products listed, the accuracy of 
            listings, or the ability of sellers to sell products or buyers to pay.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">8. Termination</h2>
          <p>
            We reserve the right to suspend or terminate your account at any time for violation 
            of these terms or for any other reason at our sole discretion.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">9. Changes to Terms</h2>
          <p>
            We may modify these terms at any time. Continued use of the platform after changes 
            constitutes acceptance of the new terms.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">10. Contact</h2>
          <p>
            For questions about these Terms of Service, please contact us at:
            <br />
            Email: legal@b2bmarket.in
          </p>
        </section>
      </div>
    </div>
  );
}
