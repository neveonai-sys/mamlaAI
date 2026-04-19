"""
Centralised Email Templates for Mamla.AI
All outgoing emails are rendered here as responsive, branded HTML.
Every classmethod returns a (subject, html_body) tuple.
"""


class EmailTemplates:
    """Branded HTML email templates for Mamla.AI."""

    COMPANY_NAME = "Mamla.AI"
    SUPPORT_EMAIL = "support@mamla.ai"
    WEBSITE_URL = "https://mamla.ai"

    # ── HTML rendering helpers ────────────────────────────────────────────────

    @classmethod
    def _html_wrap(cls, content_html: str) -> str:
        """Wrap *content_html* in the branded Mamla.AI email shell."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f0f4f8;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;background-color:#ffffff;border-radius:10px;
                      overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.10);">

          <!-- Logo header -->
          <tr>
            <td style="background-color:#0f2544;padding:24px 32px;">
              <table cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="font-family:'Palatino Linotype',Palatino,Georgia,serif;
                             font-size:30px;font-weight:700;color:#ffffff;
                             letter-spacing:1px;line-height:1;">Mamla</td>
                  <td style="padding-left:7px;vertical-align:middle;">
                    <span style="background-color:#FF9800;color:#ffffff;font-size:13px;
                                 font-weight:800;padding:3px 9px;border-radius:5px;
                                 font-family:Arial,Helvetica,sans-serif;letter-spacing:0.5px;">.AI</span>
                  </td>
                </tr>
                <tr>
                  <td colspan="2" style="padding-top:6px;font-family:Arial,Helvetica,sans-serif;
                                         font-size:9px;color:rgba(255,255,255,0.50);letter-spacing:4px;">
                    INDIA&#8217;S LEGAL INTELLIGENCE PLATFORM
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Saffron accent bar -->
          <tr><td style="height:3px;background-color:#FF9800;font-size:0;line-height:0;">&nbsp;</td></tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 40px 28px 40px;color:#1a1a2e;font-size:15px;line-height:1.75;">
              {content_html}
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td style="border-top:1px solid #e8ecf2;font-size:0;line-height:0;">&nbsp;</td></tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#f8fafc;padding:20px 40px 24px;
                       text-align:center;font-family:Arial,Helvetica,sans-serif;
                       font-size:12px;color:#6b7280;line-height:1.6;">
              Need help?&nbsp;
              <a href="mailto:{cls.SUPPORT_EMAIL}" style="color:#1a3a6b;text-decoration:none;">{cls.SUPPORT_EMAIL}</a>
              &nbsp;·&nbsp;
              <a href="{cls.WEBSITE_URL}" style="color:#1a3a6b;text-decoration:none;">{cls.WEBSITE_URL}</a><br/>
              <span style="font-size:11px;color:#9ca3af;">
                &copy; 2025 Neveon AI Technologies Pvt. Ltd.&nbsp;·&nbsp;Mamla.AI
              </span>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    @classmethod
    def get_footer(cls) -> str:
        """Legacy plain-text footer — retained for backward compatibility."""
        return (
            f"\nBest regards,\nThe {cls.COMPANY_NAME} Team\n\n"
            f"Need help? {cls.SUPPORT_EMAIL}\n"
            f"Visit us: {cls.WEBSITE_URL}\n"
        )

    # ── User Authentication & Onboarding ─────────────────────────────────────

    @classmethod
    def welcome_email(cls, fname, user_id):
        """Welcome email after successful email verification."""
        subject = f"Welcome to {cls.COMPANY_NAME} \u2014 Your Account is Active"
        content = f"""
<p>Dear <strong>{fname}</strong>,</p>
<p>Welcome to <strong>{cls.COMPANY_NAME}</strong>! We&#8217;re excited to have you on board.</p>
<p>Your account has been successfully verified and is now active. You can log in and start
   managing your legal matters with ease.</p>
<p style="background-color:#f0f4ff;border-left:4px solid #1a3a6b;padding:12px 16px;
          border-radius:4px;font-size:14px;margin:20px 0;">
  <strong>Your User ID:</strong>&nbsp;
  <code style="font-family:monospace;background:#e8ecf5;padding:2px 6px;border-radius:3px;">{user_id}</code><br/>
  <small style="color:#6b7280;">Keep this confidential &mdash; do not share it with anyone.</small>
</p>
<p><strong>Getting started:</strong></p>
<ol style="margin:8px 0 16px;padding-left:24px;color:#374151;">
  <li style="margin-bottom:6px;">Log in at
    <a href="{cls.WEBSITE_URL}" style="color:#1a3a6b;">{cls.WEBSITE_URL}</a></li>
  <li style="margin-bottom:6px;">Complete your profile setup</li>
  <li style="margin-bottom:6px;">Explore features designed to simplify your legal workflows</li>
</ol>
<p style="color:#6b7280;font-size:13px;">If you have questions, our support team is here to help.</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def email_verification_link(cls, fname, verify_link):
        """Email verification link sent during signup."""
        subject = f"Verify Your Email \u2014 {cls.COMPANY_NAME}"
        content = f"""
<p>Dear <strong>{fname}</strong>,</p>
<p>Thank you for signing up with <strong>{cls.COMPANY_NAME}</strong>.</p>
<p>Please click the button below to verify your email address. This link is valid for
   <strong>24 hours</strong>.</p>
<p style="text-align:center;margin:28px 0;">
  <a href="{verify_link}"
     style="display:inline-block;background-color:#1a3a6b;color:#ffffff;font-size:15px;
            font-weight:700;text-decoration:none;padding:13px 36px;border-radius:6px;
            letter-spacing:0.3px;">Verify My Email</a>
</p>
<p style="font-size:13px;color:#6b7280;">
  If the button does not work, paste this link into your browser:<br/>
  <a href="{verify_link}" style="color:#1a3a6b;word-break:break-all;">{verify_link}</a>
</p>
<p style="font-size:13px;color:#6b7280;">
  If you did not sign up for {cls.COMPANY_NAME}, please ignore this email.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def client_signup_invitation(cls, client_fname, lawyer_fname, lawyer_lname, signup_link):
        """Email sent to a client when their lawyer onboards them."""
        subject = f"You&#8217;ve Been Invited to Join {cls.COMPANY_NAME}"
        content = f"""
<p>Dear <strong>{client_fname}</strong>,</p>
<p>You have been invited to join <strong>{cls.COMPANY_NAME}</strong> by
   <strong>{lawyer_fname} {lawyer_lname}</strong>.</p>
<p>{cls.COMPANY_NAME} is a comprehensive legal management platform that simplifies communication
   and case management between lawyers and their clients.</p>
<p style="text-align:center;margin:28px 0;">
  <a href="{signup_link}"
     style="display:inline-block;background-color:#FF9800;color:#ffffff;font-size:15px;
            font-weight:700;text-decoration:none;padding:13px 36px;border-radius:6px;
            letter-spacing:0.3px;">Complete My Registration</a>
</p>
<p style="font-size:13px;color:#6b7280;">
  This invitation expires in <strong>24 hours</strong>. If the button does not work:<br/>
  <a href="{signup_link}" style="color:#1a3a6b;word-break:break-all;">{signup_link}</a>
</p>
<p><strong>Benefits of using {cls.COMPANY_NAME}:</strong></p>
<ul style="margin:8px 0 16px;padding-left:24px;color:#374151;">
  <li style="margin-bottom:6px;">Real-time updates on your case progress</li>
  <li style="margin-bottom:6px;">Secure communication with your legal team</li>
  <li style="margin-bottom:6px;">Document management and access</li>
  <li style="margin-bottom:6px;">Calendar and meeting scheduling</li>
</ul>
<p style="font-size:13px;color:#6b7280;">
  Did not expect this invite? Contact your lawyer or reach us at
  <a href="mailto:{cls.SUPPORT_EMAIL}" style="color:#1a3a6b;">{cls.SUPPORT_EMAIL}</a>.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def password_reset_link(cls, email_id, reset_link):
        """Password reset email."""
        subject = f"Reset Your {cls.COMPANY_NAME} Password"
        content = f"""
<p>Dear User,</p>
<p>We received a request to reset the password for <strong>{email_id}</strong> on
   {cls.COMPANY_NAME}.</p>
<p style="text-align:center;margin:28px 0;">
  <a href="{reset_link}"
     style="display:inline-block;background-color:#1a3a6b;color:#ffffff;font-size:15px;
            font-weight:700;text-decoration:none;padding:13px 36px;border-radius:6px;">
    Reset My Password</a>
</p>
<p style="font-size:13px;color:#6b7280;">
  This link expires in <strong>24 hours</strong>. If the button does not work:<br/>
  <a href="{reset_link}" style="color:#1a3a6b;word-break:break-all;">{reset_link}</a>
</p>
<p style="font-size:13px;color:#6b7280;">
  If you did not request a password reset, please ignore this email. Your account remains secure.
</p>"""
        return subject, cls._html_wrap(content)

    # ── Calendar & Meeting Management ─────────────────────────────────────────

    @classmethod
    def event_created_with_party(cls, fname, lname, start_datetime, end_datetime, meet_link=None):
        """Event creation confirmation — party B is involved."""
        subject = "Meeting Scheduled Successfully"
        link_row = (
            f'<li style="margin-bottom:6px;"><strong>Meeting Link:</strong> '
            f'<a href="{meet_link}" style="color:#1a3a6b;">{meet_link}</a></li>'
        ) if meet_link else ""
        content = f"""
<p>Dear Sir/Madam,</p>
<p>Your meeting has been successfully scheduled on <strong>{cls.COMPANY_NAME}</strong>.</p>
<table cellpadding="0" cellspacing="0" border="0"
       style="background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
              padding:16px 20px;margin:16px 0;width:100%;">
  <tr><td>
    <ul style="margin:0;padding-left:20px;color:#374151;font-size:14px;">
      <li style="margin-bottom:6px;"><strong>Start:</strong> {start_datetime}</li>
      <li style="margin-bottom:6px;"><strong>End:</strong> {end_datetime}</li>
      {link_row}
    </ul>
  </td></tr>
</table>
<p style="color:#6b7280;font-size:13px;">
  All participants have been notified. Log in to your dashboard to view or modify this event.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def event_created_solo(cls, fname, lname, start_datetime, end_datetime, meet_link=None):
        """Event creation confirmation — personal task."""
        subject = "Task Scheduled Successfully"
        link_row = (
            f'<li style="margin-bottom:6px;"><strong>Link:</strong> '
            f'<a href="{meet_link}" style="color:#1a3a6b;">{meet_link}</a></li>'
        ) if meet_link else ""
        content = f"""
<p>Dear Sir/Madam,</p>
<p>Your task has been successfully scheduled on <strong>{cls.COMPANY_NAME}</strong>.</p>
<table cellpadding="0" cellspacing="0" border="0"
       style="background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
              padding:16px 20px;margin:16px 0;width:100%;">
  <tr><td>
    <ul style="margin:0;padding-left:20px;color:#374151;font-size:14px;">
      <li style="margin-bottom:6px;"><strong>Start:</strong> {start_datetime}</li>
      <li style="margin-bottom:6px;"><strong>End:</strong> {end_datetime}</li>
      {link_row}
    </ul>
  </td></tr>
</table>
<p style="color:#6b7280;font-size:13px;">
  You will receive a reminder before the scheduled time. Log in to your dashboard to manage this task.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def event_created_participant(cls, title, start_datetime, end_datetime, meet_link=None):
        """Participant notification when added to a meeting."""
        subject = "You've Been Added to a Meeting"
        link_row = (
            f'<li style="margin-bottom:6px;"><strong>Meeting Link:</strong> '
            f'<a href="{meet_link}" style="color:#1a3a6b;">{meet_link}</a></li>'
        ) if meet_link else ""
        content = f"""
<p>Dear Sir/Madam,</p>
<p>You have been added as a participant to the meeting
   <strong>&#8220;{title}&#8221;</strong> on {cls.COMPANY_NAME}.</p>
<table cellpadding="0" cellspacing="0" border="0"
       style="background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
              padding:16px 20px;margin:16px 0;width:100%;">
  <tr><td>
    <ul style="margin:0;padding-left:20px;color:#374151;font-size:14px;">
      <li style="margin-bottom:6px;"><strong>Start:</strong> {start_datetime}</li>
      <li style="margin-bottom:6px;"><strong>End:</strong> {end_datetime}</li>
      {link_row}
    </ul>
  </td></tr>
</table>
<p style="color:#6b7280;font-size:13px;">
  Please review your schedule and attend at the scheduled time.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def event_updated_entire_series(cls, fname, lname, title, updated_fields):
        """Event series updated notification."""
        subject = "Meeting Series Updated"
        content = f"""
<p>Dear Sir/Madam,</p>
<p>Your recurring meeting <strong>&#8220;{title}&#8221;</strong> has been updated successfully.</p>
<p><strong>Updated Information:</strong></p>
<p style="background-color:#f8fafc;border-left:4px solid #FF9800;padding:12px 16px;
          border-radius:4px;font-size:14px;white-space:pre-wrap;">{updated_fields}</p>
<p style="color:#6b7280;font-size:13px;">
  Changes have been applied to <em>all occurrences</em> in this series.
  Log in to your dashboard to review the updated schedule.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def event_updated_following(cls, fname, lname, title, updated_fields):
        """Current and following events updated notification."""
        subject = "Meeting Series Updated From Selected Occurrence"
        content = f"""
<p>Dear Sir/Madam,</p>
<p>Your recurring meeting <strong>&#8220;{title}&#8221;</strong> has been updated from the
   selected occurrence onward.</p>
<p><strong>Updated Information:</strong></p>
<p style="background-color:#f8fafc;border-left:4px solid #FF9800;padding:12px 16px;
          border-radius:4px;font-size:14px;white-space:pre-wrap;">{updated_fields}</p>
<p style="color:#6b7280;font-size:13px;">
  Earlier occurrences remain unchanged.
  Log in to your dashboard to review the revised schedule.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def event_updated_single(cls, fname, lname, title, updated_fields):
        """Single event updated notification."""
        subject = "Meeting Updated"
        content = f"""
<p>Dear Sir/Madam,</p>
<p>Your meeting <strong>&#8220;{title}&#8221;</strong> has been updated successfully.</p>
<p><strong>Updated Information:</strong></p>
<p style="background-color:#f8fafc;border-left:4px solid #FF9800;padding:12px 16px;
          border-radius:4px;font-size:14px;white-space:pre-wrap;">{updated_fields}</p>
<p style="color:#6b7280;font-size:13px;">
  Log in to your dashboard to view the updated details.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def event_updated_participant(cls, title, updated_fields, scope_label='single event'):
        """Participant notification when a meeting is updated."""
        subject = "Meeting Update Notification"
        content = f"""
<p>Dear Sir/Madam,</p>
<p>The meeting <strong>&#8220;{title}&#8221;</strong> has been updated on {cls.COMPANY_NAME}.</p>
<p style="font-size:14px;color:#6b7280;"><strong>Scope:</strong> {scope_label}</p>
<p><strong>Updated Information:</strong></p>
<p style="background-color:#f8fafc;border-left:4px solid #FF9800;padding:12px 16px;
          border-radius:4px;font-size:14px;white-space:pre-wrap;">{updated_fields}</p>
<p style="color:#6b7280;font-size:13px;">
  Please review the latest details in your calendar.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def event_deleted_series(cls, fname, lname, title):
        """Event series deleted notification."""
        subject = "Meeting Series Cancelled"
        content = f"""
<p>Dear Sir/Madam,</p>
<p>The recurring meeting series <strong>&#8220;{title}&#8221;</strong> has been cancelled.</p>
<p>All occurrences have been removed from your calendar and all participants have been notified.</p>
<p style="color:#6b7280;font-size:13px;">
  If this was done in error, please create a new meeting series or contact our support team.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def event_deleted_following(cls, fname, lname, title):
        """Current and following events deleted notification."""
        subject = "Future Meetings Cancelled"
        content = f"""
<p>Dear Sir/Madam,</p>
<p>The recurring meeting <strong>&#8220;{title}&#8221;</strong> has been cancelled from the
   selected occurrence onward.</p>
<p>Earlier completed or retained occurrences remain unchanged. All affected participants have
   been notified.</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def event_deleted_single(cls, fname, lname, title):
        """Single event deleted notification."""
        subject = "Meeting Cancelled"
        content = f"""
<p>Dear Sir/Madam,</p>
<p>Your meeting <strong>&#8220;{title}&#8221;</strong> has been cancelled and removed from
   your calendar.</p>
<p>If there were other participants, they have been notified of this cancellation.</p>
<p style="color:#6b7280;font-size:13px;">
  If this was done in error, please reschedule or contact our support team.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def event_deleted_participant(cls, title, scope_label='single event'):
        """Participant notification when a meeting is cancelled."""
        subject = "Meeting Cancellation Notice"
        content = f"""
<p>Dear Sir/Madam,</p>
<p>The meeting <strong>&#8220;{title}&#8221;</strong> has been cancelled on {cls.COMPANY_NAME}.</p>
<p style="font-size:14px;color:#6b7280;"><strong>Scope:</strong> {scope_label}</p>
<p>Please update your schedule accordingly.</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def event_reminder(cls, fname, lname, title, start_time, meet_link=None):
        """Meeting reminder notification (sent from calendar events)."""
        subject = f"Reminder: Upcoming Meeting \u2014 {title}"
        link_section = (
            f'<p style="text-align:center;margin:24px 0;">'
            f'<a href="{meet_link}" style="display:inline-block;background-color:#1a3a6b;'
            f'color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;'
            f'padding:12px 28px;border-radius:6px;">Join Meeting</a></p>'
        ) if meet_link else ""
        content = f"""
<p>Dear Sir/Madam,</p>
<p>This is a reminder for your upcoming meeting.</p>
<table cellpadding="0" cellspacing="0" border="0"
       style="background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
              padding:16px 20px;margin:16px 0;width:100%;">
  <tr><td>
    <p style="margin:0;font-size:14px;color:#374151;">
      <strong>Meeting:</strong> {title}<br/>
      <strong>Time:</strong> {start_time}
    </p>
  </td></tr>
</table>
{link_section}
<p style="color:#6b7280;font-size:13px;">
  Please ensure you are prepared and available at the scheduled time.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def meeting_reminder(cls, title: str, start_time: str, window_label: str, meet_link=None):
        """
        Automated reminder email sent 1 hour or 15 minutes before a meeting.
        window_label: '1 hour' or '15 minutes'
        """
        subject = f"Reminder: Your meeting \u2018{title}\u2019 starts in {window_label}"
        link_section = (
            f'<p style="text-align:center;margin:24px 0;">'
            f'<a href="{meet_link}" style="display:inline-block;background-color:#1a3a6b;'
            f'color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;'
            f'padding:12px 28px;border-radius:6px;">Join Meeting</a></p>'
        ) if meet_link else ""
        content = f"""
<p>Hello,</p>
<p>Your upcoming meeting is starting in <strong>{window_label}</strong>.</p>
<table cellpadding="0" cellspacing="0" border="0"
       style="background-color:#fff8f0;border:1px solid #FFD08A;border-radius:8px;
              padding:16px 20px;margin:16px 0;width:100%;">
  <tr><td>
    <p style="margin:0;font-size:15px;color:#374151;">
      <strong>Meeting:</strong> {title}<br/>
      <strong>Scheduled Time:</strong> {start_time}
    </p>
  </td></tr>
</table>
{link_section}
<p style="color:#6b7280;font-size:13px;">
  Please ensure you are prepared and available at the scheduled time.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def daily_meetings_summary(cls, consolidated_meetings_text: str):
        """Daily consolidated meeting summary email."""
        subject = "Your Daily Meeting Summary \u2014 Mamla.AI"
        content = f"""
<p>Hello,</p>
<p>Here is your daily summary of scheduled meetings for today.</p>
<table cellpadding="0" cellspacing="0" border="0"
       style="background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
              padding:20px 24px;margin:16px 0;width:100%;">
  <tr><td>
    <p style="margin:0;font-size:14px;color:#374151;white-space:pre-wrap;line-height:1.8;">{consolidated_meetings_text}</p>
  </td></tr>
</table>
<p style="color:#6b7280;font-size:13px;">
  Log in to your dashboard to view full details or make changes.
</p>"""
        return subject, cls._html_wrap(content)

    # ── Document & Draft Management ───────────────────────────────────────────

    @classmethod
    def draft_ready(cls, fname, lname, draft_title):
        """Notification when a legal draft is ready for review."""
        subject = f"Your Legal Draft is Ready \u2014 {cls.COMPANY_NAME}"
        content = f"""
<p>Dear <strong>{fname} {lname}</strong>,</p>
<p>Your legal draft <strong>&#8220;{draft_title}&#8221;</strong> has been prepared and is now
   available for review.</p>
<p>You can access it by logging into your <strong>{cls.COMPANY_NAME}</strong> dashboard under
   the <em>Documents</em> section.</p>
<p style="color:#6b7280;font-size:13px;">
  Please review the draft carefully. If you need modifications or have questions, you can
  request changes through the platform.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def draft_delivery_email(cls, lawyer_fname: str, client_fname: str, draft_title: str,
                             draft_summary: str = '', note: str = '') -> tuple:
        """
        Email sent by a lawyer to a client with a legal draft attached (PDF + DOCX).
        Returns (subject, html_body) tuple.
        """
        subject = f"Legal Draft from {lawyer_fname} — {draft_title}"
        note_block = (
            f"""<div style="background:#f8fafc;border-left:3px solid #FF9800;padding:12px 16px;
                     margin:16px 0;border-radius:0 8px 8px 0;">
  <p style="margin:0;font-size:13px;color:#374151;"><strong>Note from {lawyer_fname}:</strong><br>
  {note}</p>
</div>"""
            if note else ''
        )
        summary_block = (
            f"""<p style="color:#6b7280;font-size:13px;line-height:1.6;">
  <strong>Document summary:</strong><br>{draft_summary}
</p>"""
            if draft_summary else ''
        )
        content = f"""
<p>Dear <strong>{client_fname}</strong>,</p>
<p>Your advocate <strong>{lawyer_fname}</strong> has prepared the following legal document for you
   and shared it via <strong>{cls.COMPANY_NAME}</strong>:</p>
<p style="font-size:16px;font-weight:700;color:#0f2544;">&#8220;{draft_title}&#8221;</p>
{note_block}
{summary_block}
<p>The full draft is attached to this email for your convenience.</p>
<p style="color:#6b7280;font-size:13px;">
  Please review the document carefully. If you have questions or need changes, reach out to your
  advocate or log into {cls.COMPANY_NAME} to track your case.
</p>
<p style="color:#9ca3af;font-size:12px;margin-top:24px;">
  This document was generated and shared using {cls.COMPANY_NAME}. Do not reply to this email —
  contact your advocate directly for any queries.
</p>"""
        return subject, cls._html_wrap(content)

    # ── System Notifications ──────────────────────────────────────────────────

    @classmethod
    def session_notification(cls, fname, lname, device_type, location, ip_address):
        """New login session notification."""
        subject = f"New Login to Your {cls.COMPANY_NAME} Account"
        content = f"""
<p>Dear <strong>{fname} {lname}</strong>,</p>
<p>We noticed a new login to your <strong>{cls.COMPANY_NAME}</strong> account.</p>
<table cellpadding="0" cellspacing="0" border="0"
       style="background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
              padding:16px 20px;margin:16px 0;width:100%;">
  <tr><td>
    <ul style="margin:0;padding-left:20px;color:#374151;font-size:14px;">
      <li style="margin-bottom:6px;"><strong>Device:</strong> {device_type}</li>
      <li style="margin-bottom:6px;"><strong>Location:</strong> {location}</li>
      <li style="margin-bottom:6px;"><strong>IP Address:</strong> {ip_address}</li>
      <li><strong>Time:</strong> Just now</li>
    </ul>
  </td></tr>
</table>
<p>If this was you, you can safely ignore this email.</p>
<p style="background-color:#fff3cd;border:1px solid #ffc107;border-radius:6px;
          padding:12px 16px;font-size:14px;color:#856404;">
  <strong>Not you?</strong> Please change your password immediately, review your active sessions
  in account settings, and contact
  <a href="mailto:{cls.SUPPORT_EMAIL}" style="color:#1a3a6b;">{cls.SUPPORT_EMAIL}</a>.
</p>"""
        return subject, cls._html_wrap(content)

    @classmethod
    def feedback_acknowledgment(cls, fname):
        """Acknowledgment after user submits feedback."""
        subject = f"Thank You for Your Feedback \u2014 {cls.COMPANY_NAME}"
        content = f"""
<p>Dear <strong>{fname}</strong>,</p>
<p>Thank you for taking the time to share your feedback with us.</p>
<p>Your input is invaluable in helping us improve <strong>{cls.COMPANY_NAME}</strong> and
   deliver a better experience for all our users.</p>
<p>Our team will carefully review your feedback. If you&#8217;ve raised specific concerns or
   feature requests, we&#8217;ll reach out if we need additional information.</p>
<p>We appreciate your partnership in making {cls.COMPANY_NAME} better.</p>"""
        return subject, cls._html_wrap(content)

    # ── Error & Exception Cases ───────────────────────────────────────────────

    @classmethod
    def account_verification_expired(cls, fname):
        """Notification when a verification link expires."""
        subject = f"Verification Link Expired \u2014 {cls.COMPANY_NAME}"
        content = f"""
<p>Dear <strong>{fname}</strong>,</p>
<p>Your email verification link has expired for security reasons.</p>
<p><strong>To complete your registration:</strong></p>
<ol style="margin:8px 0 16px;padding-left:24px;color:#374151;">
  <li style="margin-bottom:6px;">Return to
    <a href="{cls.WEBSITE_URL}" style="color:#1a3a6b;">{cls.WEBSITE_URL}</a></li>
  <li style="margin-bottom:6px;">Click <em>Resend Verification Email</em></li>
  <li style="margin-bottom:6px;">Check your inbox for a new verification link</li>
</ol>
<p style="color:#6b7280;font-size:13px;">
  Verification links are valid for 24 hours from registration. If you continue to experience
  issues, please contact our support team at
  <a href="mailto:{cls.SUPPORT_EMAIL}" style="color:#1a3a6b;">{cls.SUPPORT_EMAIL}</a>.
</p>"""
        return subject, cls._html_wrap(content)


# ── Utility ───────────────────────────────────────────────────────────────────

def format_datetime_for_email(datetime_str):
    """
    Format a datetime string for display in emails.
    Input:  "2024-09-17T22:01" or "2024-09-17"
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
    except Exception:
        return datetime_str  # Return as-is if parsing fails
