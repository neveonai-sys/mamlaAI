"""
Centralized Email Template Management for Mamla.ai
All email templates are maintained here for consistency and professionalism.
"""

class EmailTemplates:
    """
    Professional email templates for Mamla.ai
    All templates follow consistent branding and tone.
    """
    
    COMPANY_NAME = "Mamla.ai"
    SUPPORT_EMAIL = "support@mamla.ai"
    WEBSITE_URL = "https://mamla.ai"
    
    # Email signature footer
    FOOTER = """
Best regards,
The Mamla.ai Team

---
Need help? Contact us at {support_email}
Visit us: {website_url}
"""
    
    @classmethod
    def get_footer(cls):
        """Return formatted email footer"""
        return cls.FOOTER.format(
            support_email=cls.SUPPORT_EMAIL,
            website_url=cls.WEBSITE_URL
        )
    
    # ============================================
    # USER AUTHENTICATION & ONBOARDING
    # ============================================
    
    @classmethod
    def welcome_email(cls, fname, user_id):
        """Welcome email after successful email verification"""
        subject = f"Welcome to {cls.COMPANY_NAME} - Your Account is Active"
        body = f"""Dear {fname},

Welcome to {cls.COMPANY_NAME}! We're excited to have you on board.

Your account has been successfully verified and is now active. You can log in and start managing your legal matters with ease.

Your User ID: {user_id}
(Please keep this confidential and do not share it with anyone)

To get started:
1. Log in to your account at {cls.WEBSITE_URL}
2. Complete your profile setup
3. Explore our features designed to simplify your legal workflows

If you have any questions or need assistance, our support team is here to help.

{cls.get_footer()}"""
        return subject, body
    
    @classmethod
    def client_signup_invitation(cls, client_fname, lawyer_fname, lawyer_lname, signup_link):
        """Email sent to client when lawyer onboards them"""
        subject = f"You've Been Invited to Join {cls.COMPANY_NAME}"
        body = f"""Dear {client_fname},

You have been invited to join {cls.COMPANY_NAME} by {lawyer_fname} {lawyer_lname}.

{cls.COMPANY_NAME} is a comprehensive legal management platform designed to streamline communication and case management between lawyers and their clients.

To complete your registration and access your account, please click the link below:

{signup_link}

This invitation link will expire in 24 hours for security purposes.

Benefits of using {cls.COMPANY_NAME}:
• Real-time updates on your case progress
• Secure communication with your legal team
• Document management and access
• Calendar and meeting scheduling
• And much more

If you did not expect this invitation or have any questions, please contact your lawyer or reach out to our support team.

{cls.get_footer()}"""
        return subject, body
    
    @classmethod
    def password_reset_link(cls, email_id, reset_link):
        """Password reset email (handled by Supabase, but kept for reference)"""
        subject = "Reset Your Password"
        body = f"""Dear User,

We received a request to reset your password for your {cls.COMPANY_NAME} account.

Click the link below to create a new password:

{reset_link}

This link will expire in 24 hours for security reasons.

If you didn't request a password reset, please ignore this email or contact our support team if you have concerns.

{cls.get_footer()}"""
        return subject, body
    
    # ============================================
    # CALENDAR & MEETING MANAGEMENT
    # ============================================
    
    @classmethod
    def event_created_with_party(cls, fname, lname, start_datetime, end_datetime, meet_link=None):
        """Event creation confirmation - when party B is involved"""
        subject = "Meeting Scheduled Successfully"
        
        meeting_info = f"\nMeeting Link: {meet_link}" if meet_link else ""
        
        body = f"""Dear Sir/Madam,

Your meeting has been successfully scheduled on {cls.COMPANY_NAME}.

Meeting Details:
• Start: {start_datetime}
• End: {end_datetime}{meeting_info}

All participants have been notified. You will receive a reminder before the meeting starts.

To view or modify this event, please log in to your {cls.COMPANY_NAME} dashboard.

{cls.get_footer()}"""
        return subject, body
    
    @classmethod
    def event_created_solo(cls, fname, lname, start_datetime, end_datetime, meet_link=None):
        """Event creation confirmation - personal event"""
        subject = "Task Scheduled Successfully"
        
        meeting_info = f"\nMeeting Link: {meet_link}" if meet_link else ""
        
        body = f"""Dear Sir/Madam,

Your task has been successfully scheduled on {cls.COMPANY_NAME}.

Task Details:
• Start: {start_datetime}
• End: {end_datetime}{meeting_info}

You will receive a reminder before the scheduled time.

To view or modify this task, please log in to your {cls.COMPANY_NAME} dashboard.

{cls.get_footer()}"""
        return subject, body

    @classmethod
    def event_created_participant(cls, title, start_datetime, end_datetime, meet_link=None):
        """Participant notification when they are added to a meeting"""
        subject = "You've Been Added to a Meeting"

        meeting_info = f"\nMeeting Link: {meet_link}" if meet_link else ""

        body = f"""Dear Sir/Madam,

You have been added as a participant to the meeting \"{title}\" on {cls.COMPANY_NAME}.

Meeting Details:
• Start: {start_datetime}
• End: {end_datetime}{meeting_info}

Please review your schedule and join or attend the meeting at the scheduled time.

{cls.get_footer()}"""
        return subject, body
    
    @classmethod
    def event_updated_entire_series(cls, fname, lname, title, updated_fields):
        """Event series updated notification"""
        subject = "Meeting Series Updated"
        body = f"""Dear Sir/Madam,

Your recurring meeting "{title}" has been updated successfully.

Updated Information:
{updated_fields}

Changes have been applied to all events in this series.

To view the updated schedule, please log in to your {cls.COMPANY_NAME} dashboard.

{cls.get_footer()}"""
        return subject, body

    @classmethod
    def event_updated_following(cls, fname, lname, title, updated_fields):
        """Current and following events updated notification"""
        subject = "Meeting Series Updated From Selected Occurrence"
        body = f"""Dear Sir/Madam,

Your recurring meeting \"{title}\" has been updated from the selected occurrence onward.

Updated Information:
{updated_fields}

Earlier occurrences remain unchanged. To review the revised schedule, please log in to your {cls.COMPANY_NAME} dashboard.

{cls.get_footer()}"""
        return subject, body
    
    @classmethod
    def event_updated_single(cls, fname, lname, title, updated_fields):
        """Single event updated notification"""
        subject = "Meeting Updated"
        body = f"""Dear Sir/Madam,

Your meeting "{title}" has been updated successfully.

Updated Information:
{updated_fields}

To view the updated details, please log in to your {cls.COMPANY_NAME} dashboard.

{cls.get_footer()}"""
        return subject, body

    @classmethod
    def event_updated_participant(cls, title, updated_fields, scope_label='single event'):
        """Participant notification when a meeting is updated"""
        subject = "Meeting Update Notification"
        body = f"""Dear Sir/Madam,

The meeting \"{title}\" has been updated on {cls.COMPANY_NAME}.

Scope: {scope_label}
Updated Information:
{updated_fields}

Please review the latest details in your calendar.

{cls.get_footer()}"""
        return subject, body
    
    @classmethod
    def event_deleted_series(cls, fname, lname, title):
        """Event series deleted notification"""
        subject = "Meeting Series Cancelled"
        body = f"""Dear Sir/Madam,

The recurring meeting series "{title}" has been cancelled.

All occurrences of this meeting have been removed from your calendar. All participants have been notified of this cancellation.

If this was done in error, please create a new meeting series or contact our support team.

{cls.get_footer()}"""
        return subject, body

    @classmethod
    def event_deleted_following(cls, fname, lname, title):
        """Current and following events deleted notification"""
        subject = "Future Meetings Cancelled"
        body = f"""Dear Sir/Madam,

The recurring meeting \"{title}\" has been cancelled from the selected occurrence onward.

Earlier completed or retained occurrences remain unchanged. All affected participants have been notified.

{cls.get_footer()}"""
        return subject, body
    
    @classmethod
    def event_deleted_single(cls, fname, lname, title):
        """Single event deleted notification"""
        subject = "Meeting Cancelled"
        body = f"""Dear Sir/Madam,

Your meeting "{title}" has been cancelled.

This event has been removed from your calendar. If there were other participants, they have been notified of this cancellation.

If this was done in error, please reschedule the meeting or contact our support team.

{cls.get_footer()}"""
        return subject, body

    @classmethod
    def event_deleted_participant(cls, title, scope_label='single event'):
        """Participant notification when a meeting is cancelled"""
        subject = "Meeting Cancellation Notice"
        body = f"""Dear Sir/Madam,

The meeting \"{title}\" has been cancelled on {cls.COMPANY_NAME}.

Scope: {scope_label}

Please update your schedule accordingly.

{cls.get_footer()}"""
        return subject, body
    
    @classmethod
    def event_reminder(cls, fname, lname, title, start_time, meet_link=None):
        """Meeting reminder notification"""
        subject = f"Reminder: Upcoming Meeting - {title}"
        
        meeting_info = f"\n\nMeeting Link: {meet_link}\n(Click to join when it's time)" if meet_link else ""
        
        body = f"""Dear Sir/Madam,

This is a reminder for your upcoming meeting.

Meeting: {title}
Time: {start_time}{meeting_info}

Please ensure you're prepared and available at the scheduled time.

{cls.get_footer()}"""
        return subject, body
    
    # ============================================
    # DOCUMENT & DRAFT MANAGEMENT
    # ============================================
    
    @classmethod
    def draft_ready(cls, fname, lname, draft_title):
        """Notification when a draft is ready"""
        subject = "Your Legal Draft is Ready"
        body = f"""Dear {fname} {lname},

Your legal draft "{draft_title}" has been prepared and is now available for review.

You can access the draft by logging into your {cls.COMPANY_NAME} dashboard under the Documents section.

Please review the draft carefully. If you need any modifications or have questions, you can request changes through the platform.

{cls.get_footer()}"""
        return subject, body
    
    # ============================================
    # SYSTEM NOTIFICATIONS
    # ============================================
    
    @classmethod
    def session_notification(cls, fname, lname, device_type, location, ip_address):
        """New login session notification"""
        subject = "New Login to Your Account"
        body = f"""Dear {fname} {lname},

We noticed a new login to your {cls.COMPANY_NAME} account.

Login Details:
• Device: {device_type}
• Location: {location}
• IP Address: {ip_address}
• Time: Just now

If this was you, you can safely ignore this email.

If you don't recognize this activity, please:
1. Change your password immediately
2. Review your active sessions in account settings
3. Contact our support team

{cls.get_footer()}"""
        return subject, body
    
    @classmethod
    def feedback_acknowledgment(cls, fname):
        """Acknowledgment after user submits feedback"""
        subject = "Thank You for Your Feedback"
        body = f"""Dear {fname},

Thank you for taking the time to share your feedback with us.

Your input is invaluable in helping us improve {cls.COMPANY_NAME} and deliver a better experience for all our users.

Our team will carefully review your feedback. If you've raised any specific concerns or feature requests, we'll get back to you if we need additional information.

We appreciate your partnership in making {cls.COMPANY_NAME} better.

{cls.get_footer()}"""
        return subject, body
    
    # ============================================
    # ERROR & EXCEPTION CASES
    # ============================================
    
    @classmethod
    def account_verification_expired(cls, fname):
        """Notification when verification link expires"""
        subject = "Verification Link Expired"
        body = f"""Dear {fname},

Your email verification link has expired for security reasons.

To complete your registration, please:
1. Return to {cls.WEBSITE_URL}
2. Click on "Resend Verification Email"
3. Check your inbox for a new verification link

Verification links are valid for 24 hours from the time of registration.

If you continue to experience issues, please contact our support team.

{cls.get_footer()}"""
        return subject, body


# Utility function to format datetime for emails
def format_datetime_for_email(datetime_str):
    """
    Format datetime string for display in emails
    Input: "2024-09-17T22:01" or "2024-09-17"
    Output: "September 17, 2024 at 10:01 PM" or "September 17, 2024"
    """
    from datetime import datetime
    try:
        if 'T' in datetime_str:
            dt = datetime.fromisoformat(datetime_str)
            return dt.strftime("%B %d, %Y at %I:%M %p")
        else:
            dt = datetime.fromisoformat(datetime_str)
            return dt.strftime("%B %d, %Y")
    except:
        return datetime_str  # Return as-is if parsing fails
