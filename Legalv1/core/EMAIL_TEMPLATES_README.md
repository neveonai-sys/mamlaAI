# Email Templates System - Mamla.ai

## Overview

All email templates for Mamla.ai are now centralized in a single file: `core/email_templates.py`

This ensures:
- **Consistency**: All emails follow the same professional tone and branding
- **Maintainability**: Easy to update all email templates from one location
- **Professionalism**: Well-formatted, properly branded communications
- **Scalability**: Easy to add new templates following the established pattern

## Using Email Templates

### Basic Usage

```python
from core.email_templates import EmailTemplates

# Get an email template
subject, body = EmailTemplates.welcome_email(fname="John", user_id="john_20240101")

# Send via Celery
send_email_celery.delay(email_address, subject, body)
```

### Available Templates

#### User Authentication & Onboarding

1. **welcome_email(fname, user_id)**
   - Sent after successful email verification
   - Contains user's User ID (confidential)
   - Getting started instructions

2. **client_signup_invitation(client_fname, lawyer_fname, lawyer_lname, signup_link)**
   - Sent when lawyer onboards a new client
   - Includes signup link and platform benefits
   - Link expires in 24 hours

3. **password_reset_link(email_id, reset_link)**
   - Password reset email (reference template)
   - Supabase handles actual password reset
   - Link expires in 24 hours

#### Calendar & Meeting Management

4. **event_created_with_party(fname, lname, start_datetime, end_datetime, meet_link=None)**
   - Meeting scheduled with other participants
   - Includes meeting details and optional meeting link

5. **event_created_solo(fname, lname, start_datetime, end_datetime, meet_link=None)**
   - Personal task/event scheduled
   - Reminder notification included

6. **event_updated_entire_series(fname, lname, title, updated_fields)**
   - Recurring meeting series updated
   - Shows what fields were changed

7. **event_updated_single(fname, lname, title, updated_fields)**
   - Single event updated
   - Shows what fields were changed

8. **event_deleted_series(fname, lname, title)**
   - Entire recurring meeting series cancelled
   - All participants notified

9. **event_deleted_single(fname, lname, title)**
   - Single event cancelled
   - Participants notified

10. **event_reminder(fname, lname, title, start_time, meet_link=None)**
    - Reminder before meeting starts
    - Includes meeting link if available

#### Document & Draft Management

11. **draft_ready(fname, lname, draft_title)**
    - Legal draft is ready for review
    - Instructions to access the draft

#### System Notifications

12. **session_notification(fname, lname, device_type, location, ip_address)**
    - New login detected
    - Security alert with device details

13. **feedback_acknowledgment(fname)**
    - Thank you for feedback submission
    - Confirms feedback was received

#### Error & Exception Cases

14. **account_verification_expired(fname)**
    - Verification link expired
    - Instructions to resend verification

## Formatting Utilities

### format_datetime_for_email(datetime_str)

Formats datetime strings for professional display in emails:

```python
from core.email_templates import format_datetime_for_email

# Input: "2024-09-17T22:01"
# Output: "September 17, 2024 at 10:01 PM"

formatted = format_datetime_for_email("2024-09-17T22:01")
```

## Branding Configuration

Update branding information in `EmailTemplates` class:

```python
class EmailTemplates:
    COMPANY_NAME = "Mamla.ai"
    SUPPORT_EMAIL = "support@mamla.ai"
    WEBSITE_URL = "https://mamla.ai"
```

All templates will automatically use these values.

## Adding New Templates

To add a new email template:

1. Add a new `@classmethod` in the `EmailTemplates` class
2. Follow the naming convention: verb_noun (e.g., `document_shared`, `case_updated`)
3. Return a tuple: `(subject, body)`
4. Use consistent formatting with existing templates
5. Include the footer using `cls.get_footer()`

### Template Example

```python
@classmethod
def new_template_name(cls, param1, param2):
    """Description of when this email is sent"""
    subject = "Email Subject"
    body = f"""Dear {param1},

Your email content here...

{cls.get_footer()}"""
    return subject, body
```

## Updated Files

The following files have been updated to use the new email templates:

### User Management
- `Legalv1/users/routes/usermetadata.py` - Client signup invitations
- `Legalv1/users/supabase_views.py` - Authentication flows
- `Legalv1/users/views.py` - Welcome emails (legacy file)

### Calendar Management
- `Legalv1/calendar_management/views.py` - Event creation notifications
- `Legalv1/calendar_management/routes/createupdateevents.py` - Event CRUD operations

## Migration Notes

### Old Format
```python
# ❌ Old way - scattered throughout code
send_email_celery.delay(
    email, 
    "Calendar Task Setup",
    f"""Hello,\n\nAn event on {start} to {end}.\n\nRegards,\nLegalAI Team"""
)
```

### New Format
```python
# ✅ New way - centralized templates
subject, body = EmailTemplates.event_created_solo(fname, lname, start, end, meet_link)
send_email_celery.delay(email, subject, body)
```

## Benefits

1. **Professional Communication**: All emails maintain consistent professional tone
2. **Easy Updates**: Change branding or messaging in one place
3. **Better User Experience**: Well-formatted, clear communications
4. **Team Consistency**: All developers use the same templates
5. **Version Control**: Track all email changes in one file

## Testing

Before deploying email changes:

1. Review all template strings for typos
2. Test with sample data to verify formatting
3. Check that all dynamic values are properly interpolated
4. Verify links are correctly formatted
5. Test email rendering in different email clients

## Support

For questions or issues with email templates:
- Review this README
- Check existing templates for examples
- Follow the established patterns
- Maintain professional tone and formatting

---

Last Updated: February 28, 2026
Maintained by: Mamla.ai Development Team
