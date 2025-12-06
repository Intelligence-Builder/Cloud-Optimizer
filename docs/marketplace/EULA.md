# END USER LICENSE AGREEMENT (EULA)

## Cloud Optimizer - Software as a Service

**Effective Date**: December 6, 2025
**Version**: 1.0

This End User License Agreement ("Agreement") is entered into by and between Intelligence-Builder Inc. ("Licensor", "we", "us", or "our") and the entity or person ("Licensee", "you", or "your") subscribing to Cloud Optimizer ("Software") through AWS Marketplace.

BY SUBSCRIBING TO THE SOFTWARE THROUGH AWS MARKETPLACE, YOU AGREE TO BE BOUND BY THE TERMS OF THIS AGREEMENT. IF YOU DO NOT AGREE TO THESE TERMS, DO NOT SUBSCRIBE TO OR USE THE SOFTWARE.

---

## 1. DEFINITIONS

**1.1 "Software"** means Cloud Optimizer, a cloud security and compliance scanning platform delivered as a containerized application through AWS Marketplace.

**1.2 "Services"** means the security scanning, compliance analysis, and related functionality provided by the Software.

**1.3 "AWS Marketplace"** means Amazon Web Services' marketplace platform through which the Software is distributed.

**1.4 "Customer Data"** means any data, content, or information that you upload, submit, or generate using the Software.

**1.5 "Documentation"** means the user guides, technical documentation, and online help resources provided with the Software.

**1.6 "Subscription Term"** means the period during which you have an active paid subscription or active trial period.

**1.7 "Usage Data"** means metering information (scan counts, question counts, document analysis counts) sent to AWS Marketplace for billing purposes.

---

## 2. LICENSE GRANT

**2.1 Limited License**

Subject to your compliance with this Agreement and payment of applicable fees, Licensor grants you a limited, non-exclusive, non-transferable, non-sublicensable license to:
- Install and run the Software container in your AWS environment
- Access and use the Services for your internal business purposes
- Permit your authorized employees and contractors to use the Software
- Use the Documentation in connection with your use of the Software

**2.2 License Restrictions**

You shall NOT:
- Modify, reverse engineer, decompile, or disassemble the Software
- Remove, alter, or obscure any proprietary notices in the Software
- Distribute, sublicense, rent, lease, or lend the Software to third parties
- Use the Software to develop a competing product or service
- Use the Software in violation of applicable laws or regulations
- Exceed the user limits, account limits, or other restrictions of your subscription tier
- Attempt to bypass usage metering or license validation mechanisms
- Use the Software to process data on behalf of third parties without an MSP agreement

**2.3 Reservation of Rights**

Licensor retains all right, title, and interest in and to the Software, including all intellectual property rights. This Agreement grants you only the limited license specified in Section 2.1.

---

## 3. SUBSCRIPTION AND PAYMENT

**3.1 Subscription Tiers**

The Software is available in the following subscription tiers:
- **Free Trial**: 14-day trial with limited usage
- **Professional**: Monthly or annual subscription with usage-based pricing
- **Enterprise**: Custom subscription with negotiated terms

**3.2 Payment Terms**

All payments are processed through AWS Marketplace in accordance with AWS's terms. You agree to pay:
- Base subscription fees (Professional and Enterprise tiers)
- Usage fees based on metered dimensions (scans, questions, documents)
- Any applicable taxes

**3.3 Free Trial**

- Free trials are limited to one per organization
- Trial includes 50 scans, 500 questions, and 20 document analyses
- No credit card required for trial activation
- Trial automatically expires after 14 days unless converted to paid subscription
- One-time 7-day extension available upon request

**3.4 Usage Metering**

The Software reports usage to AWS Marketplace for billing purposes. You agree that:
- Usage is measured by: security scans, chat questions, and document analyses
- Usage is reported hourly to AWS Marketplace
- You are responsible for all usage by your authorized users
- Usage charges are non-refundable

**3.5 Price Changes**

Licensor reserves the right to modify pricing with 30 days' notice. Price changes do not affect existing annual subscriptions until renewal.

---

## 4. DATA AND PRIVACY

**4.1 Customer Data Ownership**

You retain all right, title, and interest in and to your Customer Data. You grant Licensor a limited license to process Customer Data solely to provide the Services.

**4.2 Data Storage**

- Customer Data is stored in your PostgreSQL database within your AWS account
- Licensor does not store or have access to your Customer Data
- You are responsible for database backups and disaster recovery

**4.3 Usage Data**

Licensor collects and processes Usage Data to:
- Report usage to AWS Marketplace for billing
- Monitor service performance and reliability
- Improve the Software and Services

Usage Data does NOT include:
- AWS account identifiers or credentials
- Scan results or findings
- Security vulnerabilities detected
- Personal information or PII

**4.4 Data Processing Agreement**

For Enterprise customers subject to GDPR or similar regulations, a separate Data Processing Agreement (DPA) is available upon request.

**4.5 Data Security**

Licensor implements commercially reasonable security measures to protect the Software, including:
- Encryption of data in transit (TLS 1.2+)
- Secure coding practices and regular security testing
- Vulnerability disclosure program
- Security incident response procedures

**4.6 Data Retention**

Upon termination or expiration of your subscription:
- Customer Data remains in your database (under your control)
- We may retain Usage Data for up to 3 years for billing and compliance purposes
- You may export your data during the subscription term and for 30 days after termination

---

## 5. SUPPORT AND UPDATES

**5.1 Support Services**

Support is provided based on your subscription tier:
- **Free Trial**: Community support via Slack
- **Professional**: Email support with 24-hour response SLA
- **Enterprise**: Dedicated support with 4-hour response SLA

**5.2 Software Updates**

Licensor may release updates, patches, and new versions of the Software. You are responsible for:
- Applying updates to your deployed container
- Testing updates before production deployment
- Maintaining compatible database and infrastructure

**5.3 Maintenance Windows**

Licensor may perform maintenance that temporarily affects availability. We will provide reasonable notice for planned maintenance.

---

## 6. WARRANTIES AND DISCLAIMERS

**6.1 Limited Warranty**

Licensor warrants that the Software will perform substantially in accordance with the Documentation during the Subscription Term.

**6.2 Warranty Remedies**

Your exclusive remedy for breach of the limited warranty is:
- Professional tier: Service credits for downtime exceeding SLA
- Enterprise tier: Service credits or refund at Licensor's discretion

**6.3 DISCLAIMER OF WARRANTIES**

EXCEPT AS EXPRESSLY PROVIDED IN SECTION 6.1, THE SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND. LICENSOR DISCLAIMS ALL OTHER WARRANTIES, EXPRESS OR IMPLIED, INCLUDING:
- MERCHANTABILITY
- FITNESS FOR A PARTICULAR PURPOSE
- NON-INFRINGEMENT
- ACCURACY OR COMPLETENESS OF SCAN RESULTS
- DETECTION OF ALL SECURITY VULNERABILITIES

YOU ACKNOWLEDGE THAT:
- The Software assists with security analysis but does not guarantee complete security
- Scan results may contain false positives or false negatives
- You remain solely responsible for your AWS security and compliance
- The Software is not a substitute for professional security consulting

---

## 7. LIMITATION OF LIABILITY

**7.1 EXCLUSION OF DAMAGES**

TO THE MAXIMUM EXTENT PERMITTED BY LAW, LICENSOR SHALL NOT BE LIABLE FOR:
- INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES
- LOSS OF PROFITS, REVENUE, DATA, OR BUSINESS OPPORTUNITIES
- COST OF SUBSTITUTE GOODS OR SERVICES
- SECURITY BREACHES OR DATA LOSS NOT CAUSED BY LICENSOR'S GROSS NEGLIGENCE

**7.2 LIABILITY CAP**

LICENSOR'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THIS AGREEMENT SHALL NOT EXCEED THE AMOUNTS PAID BY YOU IN THE 12 MONTHS PRECEDING THE CLAIM.

**7.3 Exceptions**

The limitations in this Section 7 do not apply to:
- Your breach of Section 2.2 (License Restrictions)
- Your indemnification obligations under Section 8
- Claims arising from gross negligence or willful misconduct

---

## 8. INDEMNIFICATION

**8.1 Your Indemnification**

You agree to indemnify, defend, and hold harmless Licensor from claims arising from:
- Your use of the Software in violation of this Agreement
- Your violation of applicable laws or regulations
- Your Customer Data or its processing
- Claims by your employees, contractors, or end users

**8.2 Licensor's Indemnification**

Licensor agrees to indemnify you from third-party claims that the Software infringes intellectual property rights, provided you:
- Notify Licensor promptly in writing
- Grant Licensor sole control of the defense and settlement
- Provide reasonable cooperation

**8.3 Remedies for Infringement**

If the Software is found to infringe, Licensor may, at its option:
- Obtain a license for you to continue using the Software
- Modify the Software to be non-infringing
- Replace the Software with non-infringing equivalent
- Terminate this Agreement and refund pro-rated fees

---

## 9. TERM AND TERMINATION

**9.1 Term**

This Agreement begins when you subscribe via AWS Marketplace and continues until terminated as provided herein.

**9.2 Termination for Convenience**

- You may cancel your subscription through AWS Marketplace
- Monthly subscriptions: Effective end of current billing period
- Annual subscriptions: No refund, but may pause subscription

**9.3 Termination for Cause**

Either party may terminate immediately if the other party:
- Materially breaches this Agreement and fails to cure within 30 days
- Becomes insolvent or subject to bankruptcy proceedings
- Ceases business operations

**9.4 Suspension**

Licensor may suspend your access immediately if:
- You breach Section 2.2 (License Restrictions)
- Your account is used for illegal activities
- Payment fails or chargebacks occur
- You exceed usage limits without upgrading

**9.5 Effect of Termination**

Upon termination:
- Your license to use the Software terminates immediately
- You must cease all use of the Software
- Customer Data remains in your database (no deletion by Licensor)
- You may export data for 30 days post-termination
- Sections 4 (Data), 6.3 (Disclaimers), 7 (Liability), 8 (Indemnification), and 11 (General) survive

---

## 10. COMPLIANCE AND EXPORT

**10.1 Compliance**

You agree to use the Software in compliance with:
- All applicable federal, state, and international laws
- AWS Acceptable Use Policy
- This Agreement and Documentation

**10.2 Export Control**

The Software is subject to U.S. export control laws. You represent that you:
- Are not located in, or a national of, a U.S. embargoed country
- Are not on any U.S. government restricted party list
- Will not export or re-export the Software in violation of export laws

**10.3 Prohibited Uses**

You may not use the Software:
- In connection with nuclear, chemical, or biological weapons
- For any illegal or fraudulent purpose
- To violate the privacy or security rights of third parties
- To transmit malware, viruses, or harmful code

---

## 11. GENERAL PROVISIONS

**11.1 Governing Law**

This Agreement is governed by the laws of the State of Delaware, USA, without regard to conflict of law principles.

**11.2 Dispute Resolution**

Any disputes shall be resolved through:
1. Good faith negotiations for 30 days
2. Binding arbitration under AAA Commercial Arbitration Rules
3. Venue: Delaware, USA
4. Language: English

**11.3 Entire Agreement**

This Agreement, together with the AWS Marketplace terms, constitutes the entire agreement between the parties and supersedes all prior agreements.

**11.4 Amendments**

Licensor may modify this Agreement by providing 30 days' notice via email or in-app notification. Continued use constitutes acceptance of modified terms.

**11.5 Assignment**

You may not assign this Agreement without Licensor's prior written consent. Licensor may assign without consent.

**11.6 Severability**

If any provision is found invalid, the remaining provisions remain in effect.

**11.7 Waiver**

Failure to enforce any provision does not constitute a waiver.

**11.8 Force Majeure**

Neither party is liable for delays caused by events beyond reasonable control (natural disasters, war, pandemics, AWS outages).

**11.9 Notices**

Notices must be sent to:
- **To Licensor**: legal@intelligence-builder.com
- **To You**: Email address on file with AWS Marketplace

**11.10 Independent Contractors**

The parties are independent contractors. This Agreement does not create a partnership, joint venture, or agency relationship.

**11.11 Third-Party Beneficiaries**

There are no third-party beneficiaries to this Agreement.

**11.12 Publicity**

Licensor may identify you as a customer in marketing materials unless you opt out by emailing marketing@intelligence-builder.com.

---

## 12. CONTACT INFORMATION

**Intelligence-Builder Inc.**
Legal Department
123 Security Boulevard
San Francisco, CA 94105
USA

Email: legal@intelligence-builder.com
Phone: +1 (555) 123-4567
Website: https://intelligence-builder.com

For technical support: support@cloudoptimizer.io
For sales inquiries: sales@cloudoptimizer.io

---

## ACCEPTANCE

BY SUBSCRIBING TO CLOUD OPTIMIZER THROUGH AWS MARKETPLACE, YOU ACKNOWLEDGE THAT YOU HAVE READ THIS AGREEMENT, UNDERSTAND IT, AND AGREE TO BE BOUND BY ITS TERMS AND CONDITIONS.

If you are entering into this Agreement on behalf of an organization, you represent and warrant that you have the authority to bind that organization to these terms.

---

**End User License Agreement - Cloud Optimizer**
**Copyright © 2025 Intelligence-Builder Inc. All rights reserved.**

Last Updated: December 6, 2025
Version: 1.0
