// Legal documents rendered inside LegalModal (opened from the footer).
export const LEGAL_DOCS = {
  terms: {
    title: 'Terms of Service',
    date: 'Effective Date: 1 January 2026 | Governing Law: Indian Law',
    sections: [
      { heading: '1. Acceptance of Terms', body: 'By accessing or using the Mamla.AI platform, operated by Neveon AI Technologies Pvt. Ltd. ("Company"), you agree to these Terms. This constitutes a legally binding agreement under the Information Technology Act, 2000.' },
      { heading: '2. Eligibility', body: 'The Platform is intended solely for enrolled advocates, law firms, and legal professionals in India. By registering, you represent that you are enrolled with a State Bar Council under the Advocates Act, 1961, or an authorised representative thereof.' },
      { heading: '3. Not Legal Advice', body: 'Mamla.AI provides AI-powered tools to assist legal professionals. The Platform does not provide legal advice and does not create an advocate-client relationship. All AI-generated content must be reviewed by a qualified legal professional before use in any legal proceeding.' },
      { heading: '4. Data Processing & Confidentiality', body: 'All data is processed under AES-256 encryption. Client matter content will not be used for training AI models without explicit opt-in consent. Data is stored within India in compliance with the Digital Personal Data Protection Act, 2023.' },
      { heading: '5. Limitation of Liability', body: "The Company's total aggregate liability shall not exceed the amount paid by you in the three months preceding the claim. The Company is not liable for consequences of using unreviewed AI-generated output in legal proceedings." },
      { heading: '6. Governing Law & Disputes', body: 'These Terms are governed by Indian law. Unresolved disputes shall be referred to arbitration under the Arbitration and Conciliation Act, 1996, with the seat at Kolkata, West Bengal.' },
      { heading: '7. Grievance Officer', body: 'Designated Grievance Officer: RM, Neveon AI Technologies Pvt. Ltd. Email: neveon.ai@gmail.com. Complaints acknowledged within 24 hours and resolved within 30 days (IT Act, 2000).' },
    ],
  },
  privacy: {
    title: 'Privacy Policy',
    date: 'Effective Date: 1 January 2026 | Compliance: DPDP Act 2023 & IT Act 2000',
    sections: [
      { heading: 'Data We Collect', body: 'Account data (name, email, Bar enrollment number), professional data (matter details, documents, drafts), usage data (session logs, feature interactions), and device data (IP address for security purposes).' },
      { heading: 'How We Use Your Data', body: 'To provide and improve the Platform; to process AI requests; to send service communications. We do not sell your data to third parties under any circumstances.' },
      { heading: 'AI & Training Data', body: 'Your matter-specific content is not used to train AI models unless you explicitly opt in via written agreement. Aggregate anonymised usage patterns may be used to improve the Platform.' },
      { heading: 'Data Storage & Security', body: 'All data is stored on servers in India. We apply AES-256 at rest and TLS 1.3 in transit. Access is restricted by role-based controls and periodic security audits are conducted.' },
      { heading: 'Your Rights (DPDP Act, 2023)', body: 'Right to access, correction, erasure (subject to legal holds), grievance redressal, and right to nominate a representative to exercise rights on your behalf.' },
      { heading: 'Contact for Privacy', body: 'Grievance Officer: RM — neveon.ai@gmail.com.' },
    ],
  },
  refund: {
    title: 'Refund & Cancellation Policy',
    date: 'Effective Date: 1 January 2026',
    sections: [
      { heading: 'Cancellations', body: 'You may cancel at any time. Cancellations take effect at the end of the current billing cycle. You retain full access until the cycle ends.' },
      { heading: 'Refunds', body: 'We offer a 7-day money-back guarantee for new subscribers. After the 7-day window, subscriptions are non-refundable except for documented technical failures (72+ continuous hours) or duplicate billing.' },
      { heading: 'Annual Plans', body: 'Annual plan refunds for unused months are available within 30 days of purchase on a pro-rata basis. After 30 days, no refund is available.' },
      { heading: 'How to Request', body: 'Email neveon.ai@gmail.com with your registered email and reason. Refunds are processed within 7–10 business days to your original payment method.' },
    ],
  },
  disclaimer: {
    title: 'Legal Disclaimer',
    date: null,
    sections: [
      { heading: 'Not Legal Advice', body: 'Mamla.AI is a technology platform for qualified legal professionals. Nothing on this Platform constitutes legal advice or creates an advocate-client relationship between Neveon AI Technologies Pvt. Ltd. and any user or their clients.' },
      { heading: 'AI Output Accuracy', body: 'AI-generated content may contain errors or outdated legal references. All output must be reviewed and approved by the responsible advocate before use in any court filing, legal notice, or client advice.' },
      { heading: 'Court Data', body: 'Case data and judicial statistics from government portals are provided for informational convenience only. Always verify directly on official portals before taking any procedural step.' },
      { heading: 'Professional Responsibility', body: 'The advocate remains solely responsible for the quality, accuracy, and ethical standing of all work product under the Advocates Act, 1961 and Bar Council of India Rules.' },
    ],
  },
};
